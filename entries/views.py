import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, HttpResponse, \
    HttpResponseRedirect, render, render_to_response
from django.template.response import TemplateResponse
from django.views import generic

from braces.views import LoginRequiredMixin

from activitylog.models import ActivityLog

from payments.forms import PayPalPaymentsListForm, PayPalPaymentsEntryForm
from payments.models import create_entry_paypal_transaction

from .forms import EntryCreateUpdateForm, SelectedEntryUpdateForm
from .email_helpers import send_pp_email
from .models import CATEGORY_CHOICES_DICT, Entry, VIDEO_ENTRY_FEES, \
    SELECTED_ENTRY_FEES, WITHDRAWAL_FEE
from .utils import check_partner_email, entries_open
from .views_utils import DataPolicyAgreementRequiredMixin

"""
Enter Now link --> Entry form page

If not logged in: log in or register
If logged in but no disclaimer: disclaimer form link
If logged in and disclaimer but not already entered: Entry form
If already entered: Entry status (pending/accepted/unsuccessful)
"""


def get_paypal_dict(
        host, cost, item_name, invoice_id, custom,
        paypal_email=settings.DEFAULT_PAYPAL_EMAIL, quantity=1):

    paypal_dict = {
        "business": paypal_email,
        "amount": cost,
        "item_name": item_name,
        "custom": custom,
        "invoice": invoice_id,
        "currency_code": "GBP",
        "quantity": quantity,
        "notify_url": host + reverse('paypal-ipn'),
        "return_url": host + reverse('payments:paypal_confirm'),
        "cancel_return": host + reverse('payments:paypal_cancel'),

    }
    return paypal_dict


def permission_denied(request):
    return render(request, 'entries/permission_denied.html')


def entries_home(request):
    context = {
        "final_date": settings.FINAL_DATE,
        "final_times": settings.FINAL_TIMES,
    }
    return render(request, 'entries/home.html', context)


def judging_criteria(request):
    curr_dir = os.path.dirname(os.path.realpath(__file__))
    file = 'files/Judges2017.pdf'
    return pdf_view(os.path.join(curr_dir, file))


def pdf_view(filepath):
    try:
        return FileResponse(
            open(filepath, 'rb'),
            content_type='application/pdf'
        )
    except FileNotFoundError:
        raise Http404()


class EntryListView(LoginRequiredMixin, generic.ListView):
    model = Entry
    context_object_name = 'entries_list'
    template_name = 'entries/user_entries.html'

    def get_queryset(self):
        return Entry.objects.select_related('user').filter(
            user=self.request.user, entry_year=settings.CURRENT_ENTRY_YEAR
        )

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(EntryListView, self).get_context_data(**kwargs)

        entries = []
        for entry in self.object_list:
            paypal_video_form = None
            paypal_selected_form = None
            if not entry.withdrawn:
                host = 'http://{}'.format(self.request.META.get('HTTP_HOST'))
                if entry.status == 'submitted' and not entry.video_entry_paid:
                    # ONLY DO THIS IF PAYPAL BUTTON NEEDED
                    invoice_id = create_entry_paypal_transaction(
                        self.request.user, entry, 'video').invoice_id
                    paypal_video_form = PayPalPaymentsListForm(
                        initial=get_paypal_dict(
                            host,
                            VIDEO_ENTRY_FEES[entry.category],
                            'Video submission fee for {} category'.format(
                                CATEGORY_CHOICES_DICT[entry.category]
                            ),
                            invoice_id,
                            'video {}'.format(entry.id),
                            paypal_email=settings.DEFAULT_PAYPAL_EMAIL,
                        )
                    )

                if entry.status in ['selected_confirmed'] and not \
                        entry.selected_entry_paid:
                    # ONLY DO THIS IF PAYPAL BUTTON NEEDED
                    invoice_id = create_entry_paypal_transaction(
                        self.request.user, entry, 'selected').invoice_id
                    paypal_selected_form = PayPalPaymentsListForm(
                        initial=get_paypal_dict(
                            host,
                            SELECTED_ENTRY_FEES[entry.category],
                            'Entry fee for {} category'.format(
                                CATEGORY_CHOICES_DICT[entry.category]
                            ),
                            invoice_id,
                            'selected {}'.format(entry.id),
                            paypal_email=settings.DEFAULT_PAYPAL_EMAIL,
                        )
                    )

            can_delete = True if entry.status == 'in_progress' \
                and not entry.withdrawn else False

            entrydict = {
                'instance': entry,
                'paypal_video_form': paypal_video_form,
                'paypal_selected_form': paypal_selected_form,
                'can_delete': can_delete,
            }
            entries.append(entrydict)
        context['entries'] = entries
        return context


class EntryMixin(object):

    def form_valid(self, form):
        entry = form.save(commit=False)
        entry.user = self.request.user

        if entry.id:
            new = False
        else:
            new = True

        if self.request.POST.get('submitted', None):
            action = 'submitted'
        elif self.request.POST.get('saved', None):
            action = 'saved'
        else:
            action = 'cat_changed'

        if action == 'cat_changed':
            if entry.id:
                entry.save()
                return HttpResponseRedirect(
                    reverse('entries:edit_entry', args=[entry.entry_ref])
                )
            else:
                self.request.session['form_data'] = self.request.POST
                return HttpResponseRedirect(reverse('entries:create_entry'))

        if entry.status == 'in_progress' and action == 'submitted':
            entry.status = 'submitted'
            first_submission = True
        else:
            first_submission = False
        entry.save()

        if first_submission:
            ctx = {
                'entry': entry,
                'category': CATEGORY_CHOICES_DICT[entry.category]
            }
            send_pp_email(
                self.request, 'Entry submitted', ctx,
                'entries/email/entry_submitted.txt',
                'entries/email/entry_submitted.html',
                to_list=[self.request.user.email]
            )

            ActivityLog.objects.create(
                log="Entry {entry_id} ({category}) - user {username} - "
                    "{action}".format(
                    entry_id=entry.id,
                    category=CATEGORY_CHOICES_DICT[entry.category],
                    username=self.request.user.username,
                    action='created and submitted' if new else 'submitted'
                )
            )
            return HttpResponseRedirect(
                reverse('entries:video_payment', args=[entry.entry_ref])
            )
        ActivityLog.objects.create(
            log="Entry {entry_id} ({category}) - user {username} - "
                "{action1} and {action2}".format(
                entry_id=entry.id,
                category=CATEGORY_CHOICES_DICT[entry.category],
                username=self.request.user.username,
                action1='created' if new else 'edited',
                action2=action
            )
        )
        messages.success(self.request, self.success_message.format(action))
        return HttpResponseRedirect(self.get_success_url())

    def get_form_kwargs(self):
        kwargs = super(EntryMixin, self).get_form_kwargs()
        kwargs.update({'user': self.request.user})
        initial_data = self.request.session.get('form_data', {})
        if initial_data:
            del self.request.session['form_data']
        kwargs.update({'initial_data': initial_data})
        return kwargs

    def get_success_url(self):
        return reverse('entries:user_entries')


class EntryCreateView(
    EntryMixin, DataPolicyAgreementRequiredMixin, LoginRequiredMixin,
    generic.CreateView
):
    model = Entry
    template_name = 'entries/entry_create_update.html'
    form_class = EntryCreateUpdateForm
    success_message = 'Your entry has been {}'

    def dispatch(self, request, *args, **kwargs):
        is_open = entries_open()
        if not is_open:
            return HttpResponseRedirect(reverse('permission_denied'))
        return super(EntryMixin, self).dispatch(request, *args, **kwargs)


class EntryUpdateView(
    EntryMixin, DataPolicyAgreementRequiredMixin, LoginRequiredMixin,
    generic.UpdateView
):

    model = Entry
    template_name = 'entries/entry_create_update.html'
    form_class = EntryCreateUpdateForm
    success_message = 'Your entry has been {}'

    def get_object(self, queryset=None):
        ref = self.kwargs.get('ref')
        return get_object_or_404(Entry, entry_ref=ref, user=self.request.user)


class SelectedEntryUpdateView(
    DataPolicyAgreementRequiredMixin, LoginRequiredMixin, generic.UpdateView
):

    model = Entry
    template_name = 'entries/selected_entry_update.html'
    form_class = SelectedEntryUpdateForm
    success_message = 'Your entry has been {}'

    def dispatch(self, request, *args, **kwargs):
        # redirect if not status "selected" or "selected_confirmed"
        if not request.user.is_anonymous:
            entry = self.get_object()
            if entry.status not in ["selected", "selected_confirmed"] or \
                    entry.withdrawn:
                return HttpResponseRedirect(reverse('permission_denied'))
        return super(SelectedEntryUpdateView, self).dispatch(
            request, *args, **kwargs
        )

    def get_object(self, queryset=None):
        ref = self.kwargs.get('ref')
        return get_object_or_404(Entry, entry_ref=ref, user=self.request.user)

    def get_success_url(self):
        return reverse('entries:user_entries')

    def form_valid(self, form):
        entry = form.save()
        ActivityLog.objects.create(
            log="Selected entry {entry_id} ({category}) - user {username} - "
                "updated".format(
                    entry_id=entry.id,
                    category=CATEGORY_CHOICES_DICT[entry.category],
                    username=self.request.user.username,
                )
        )
        return super(SelectedEntryUpdateView, self).form_valid(form)


class EntryDeleteView(LoginRequiredMixin, generic.DeleteView):
    model = Entry
    success_message = 'Entry has been deleted'
    template_name = 'entries/delete_withdraw_entry.html'
    context_object_name = 'entry'

    def dispatch(self, request, *args, **kwargs):
        # redirect if not status "in_progress"
        if not request.user.is_anonymous:
            entry = self.get_object()
            if entry.status != "in_progress":
                return HttpResponseRedirect(reverse('permission_denied'))
        return super(EntryDeleteView, self).dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('entries:user_entries')
    
    def get_object(self, queryset=None):
        ref = self.kwargs.get('ref')
        return get_object_or_404(Entry, entry_ref=ref, user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super(EntryDeleteView, self).get_context_data(**kwargs)
        context['action'] = 'delete'
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Your entry was deleted')
        entry = self.get_object()
        ActivityLog.objects.create(
            log="In progress entry {entry_id} ({category}) - user {username} - "
                "deleted".format(
                    entry_id=entry.id,
                    category=CATEGORY_CHOICES_DICT[entry.category],
                    username=self.request.user.username,
                )
        )
        return super(EntryDeleteView, self).delete(request, *args, **kwargs)


class EntryWithdrawView(LoginRequiredMixin, generic.UpdateView):
    """
    An update view for withdrawing from a category
    """
    model = Entry
    template_name = 'entries/delete_withdraw_entry.html'
    success_message = 'Your entry has been withdrawn'
    fields = ('id',)

    def dispatch(self, request, *args, **kwargs):
        # redirect if already withdrawn
        if not request.user.is_anonymous:
            entry = self.get_object()
            if entry.withdrawn :
                return HttpResponseRedirect(reverse('permission_denied'))
        return super(EntryWithdrawView, self).dispatch(
            request, *args, **kwargs
        )

    def get_object(self, queryset=None):
        ref = self.kwargs.get('ref')
        return get_object_or_404(Entry, entry_ref=ref, user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super(EntryWithdrawView, self).get_context_data(**kwargs)
        context['action'] = 'withdraw'
        return context

    def form_valid(self, form):
        entry = form.save(commit=False)
        entry.withdrawn = True
        entry.save()

        messages.success(self.request, self.success_message)

        if entry.status == 'selected_confirmed':
            # Email User
            ctx = {
                'entry': entry,
                'category': CATEGORY_CHOICES_DICT[entry.category],
            }
            send_pp_email(
                self.request, 'Entry withdrawn', ctx,
                'entries/email/entry_withdrawn_after_selection.txt',
                'entries/email/entry_withdrawn_after_selection.html',
                to_list=[self.request.user.email]
            )

        if entry.status in ["selected", 'selected_confirmed']:
            # email PP
            ctx = {
                'entry': entry,
                'category': CATEGORY_CHOICES_DICT[entry.category],
                'status_at_withdrawal': 'selected'
            }
            send_pp_email(
                self.request, 'Entry withdrawn', ctx,
                'entries/email/entry_withdrawn_after_selection_to_pp.txt',
                'entries/email/entry_withdrawn_after_selection_to_pp.html',
                to_list=[settings.DEFAULT_STUDIO_EMAIL]
            )

        ActivityLog.objects.create(
            log="Entry {entry_id} ({category}) - status {status} - user {username} - "
                "withdrawn".format(
                    entry_id=entry.id,
                    category=CATEGORY_CHOICES_DICT[entry.category],
                    status=entry.status,
                    username=self.request.user.username,
                )
        )

        if entry.status == 'selected_confirmed':
            return HttpResponseRedirect(
                reverse('entries:withdrawal_payment', args=[entry.entry_ref])
            )
        return HttpResponseRedirect(reverse('entries:user_entries'))


@login_required
def entry_video_payment(request, ref):
    entry = get_object_or_404(Entry, entry_ref=ref)
    template_name = 'entries/video_payment.html'

    context = {
        'entry': entry,
        'already_paid': entry.video_entry_paid,
        'in_progress': entry.status == 'in_progress',
        'not_selected_confirmed': entry.status != 'selected_confirmed',
        'withdrawn': entry.withdrawn
    }

    if not entry.video_entry_paid and not \
            entry.status == 'in_progress' and not entry.withdrawn:
        host = 'http://{}'.format(request.META.get('HTTP_HOST'))
        invoice_id = create_entry_paypal_transaction(
            request.user, entry, 'video').invoice_id
        paypalform = PayPalPaymentsEntryForm(
            initial=get_paypal_dict(
                host,
                VIDEO_ENTRY_FEES[entry.category],
                'Video submission fee for {} category'.format(
                    CATEGORY_CHOICES_DICT[entry.category]
                ),
                invoice_id,
                'video {}'.format(entry.id),
                paypal_email=settings.DEFAULT_PAYPAL_EMAIL,
            )
        )
        context.update({
            'paypalform': paypalform,
            'fee': VIDEO_ENTRY_FEES[entry.category]
        })

    return TemplateResponse(request, template_name, context)


def check_partner(request):
    email = request.GET.get('email')
    context = {'check': True, 'email': email}
    if email:
        partner_check_dict, _ = check_partner_email(email)
        context.update(**partner_check_dict)

    return render_to_response(
        'entries/includes/partner_check.txt', context
    )


class EntryConfirmView(
    LoginRequiredMixin, DataPolicyAgreementRequiredMixin, generic.UpdateView
):
    """
    An update view for confirming entry selection
    """
    model = Entry
    template_name = 'entries/confirm_entry.html'
    fields = ('id',)

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_anonymous:
            # redirect if not status "selected"
            entry = self.get_object()
            if entry.status != "selected" or entry.withdrawn :
                return HttpResponseRedirect(reverse('permission_denied'))
        return super(EntryConfirmView, self).dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        ref = self.kwargs.get('ref')
        return get_object_or_404(Entry, entry_ref=ref, user=self.request.user)

    def form_valid(self, form):
        entry = form.save(commit=False)
        entry.status = "selected_confirmed"
        entry.save()

        # Email User
        ctx = {
            'entry': entry,
            'category': CATEGORY_CHOICES_DICT[entry.category],
        }
        send_pp_email(
            self.request, 'Finals place confirmed', ctx,
            'entries/email/entry_confirmed.txt',
            'entries/email/entry_confirmed.html',
            to_list=[self.request.user.email]
        )

        ActivityLog.objects.create(
            log="Selected entry {entry_id} ({category}) - user {username} - "
                "confirmed".format(
                    entry_id=entry.id,
                    category=CATEGORY_CHOICES_DICT[entry.category],
                    username=self.request.user.username,
                )
        )

        return HttpResponseRedirect(
            reverse('entries:selected_payment', args=[entry.entry_ref])
        )

@login_required
def entry_selected_payment(request, ref):
    entry = get_object_or_404(Entry, entry_ref=ref, user=request.user)
    template_name = 'entries/selected_payment.html'

    context = {
        'entry': entry,
        'already_paid': entry.selected_entry_paid,
        'not_selected_confirmed': entry.status != 'selected_confirmed',
        'withdrawn': entry.withdrawn
    }

    if entry.status == 'selected_confirmed' and not \
            entry.withdrawn and not entry.selected_entry_paid:
        host = 'http://{}'.format(request.META.get('HTTP_HOST'))
        invoice_id = create_entry_paypal_transaction(
            request.user, entry, 'selected').invoice_id
        paypalform = PayPalPaymentsEntryForm(
            initial=get_paypal_dict(
                host,
                SELECTED_ENTRY_FEES[entry.category],
                'Entry fee for {} category'.format(
                    CATEGORY_CHOICES_DICT[entry.category]
                ),
                invoice_id,
                'selected {}'.format(entry.id),
                paypal_email=settings.DEFAULT_PAYPAL_EMAIL,
            )
        )
        context.update({
            'paypalform': paypalform,
            'fee': SELECTED_ENTRY_FEES[entry.category]
        })

    return TemplateResponse(request, template_name, context)


@login_required
def entry_withdrawal_payment(request, ref):
    entry = get_object_or_404(Entry, entry_ref=ref, user=request.user)
    template_name = 'entries/withdrawal_payment.html'

    context = {'entry': entry}

    if not (entry.status == 'selected_confirmed' and entry.withdrawn) \
            or entry.withdrawal_fee_paid:
        return HttpResponseRedirect(reverse('permission_denied'))
    else:
        host = 'http://{}'.format(request.META.get('HTTP_HOST'))
        invoice_id = create_entry_paypal_transaction(
            request.user, entry, 'withdrawal').invoice_id
        paypalform = PayPalPaymentsEntryForm(
            initial=get_paypal_dict(
                host,
                WITHDRAWAL_FEE,
                'Withdrawal fee for {} category'.format(
                    CATEGORY_CHOICES_DICT[entry.category]
                ),
                invoice_id,
                'withdrawal {}'.format(entry.id),
                paypal_email=settings.DEFAULT_PAYPAL_EMAIL,
            )
        )
        context.update({
            'paypalform': paypalform,
            'fee': WITHDRAWAL_FEE
        })

    return TemplateResponse(request, template_name, context)
