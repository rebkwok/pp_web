from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, HttpResponseRedirect, \
    render, render_to_response

from django.template.response import TemplateResponse
from django.views import generic

from braces.views import LoginRequiredMixin

from payments.forms import PayPalPaymentsListForm, PayPalPaymentsVideoForm
from payments.models import create_entry_paypal_transaction

from .forms import EntryCreateUpdateForm, SelectedEntryUpdateForm
from .models import CATEGORY_CHOICES_DICT, Entry, VIDEO_ENTRY_FEES, \
    SELECTED_ENTRY_FEES
from .utils import check_partner_email

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
    return render(request, 'entries/home.html')


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
            return HttpResponseRedirect(
                reverse('entries:video_payment', args=[entry.entry_ref])
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


class EntryCreateView(LoginRequiredMixin, EntryMixin, generic.CreateView):
    model = Entry
    template_name = 'entries/entry_create_update.html'
    form_class = EntryCreateUpdateForm
    success_message = 'Your entry has been {}'


class EntryUpdateView(LoginRequiredMixin, EntryMixin, generic.UpdateView):

    model = Entry
    template_name = 'entries/entry_create_update.html'
    form_class = EntryCreateUpdateForm
    success_message = 'Your entry has been {}'

    def get_object(self, queryset=None):
        ref = self.kwargs.get('ref')
        return get_object_or_404(Entry, entry_ref=ref)


class SelectedEntryUpdateView(LoginRequiredMixin, generic.UpdateView):

    model = Entry
    template_name = 'entries/selected_entry_update.html'
    form_class = SelectedEntryUpdateForm
    success_message = 'Your entry has been {}'

    def get_object(self, queryset=None):
        ref = self.kwargs.get('ref')
        return get_object_or_404(Entry, entry_ref=ref)

    def get_success_url(self):
        return reverse('entries:user_entries')


class EntryDeleteView(LoginRequiredMixin, generic.DeleteView):
    model = Entry
    success_message = 'Entry has been deleted'
    template_name = 'entries/delete_withdraw_entry.html'
    context_object_name = 'entry'

    def get_success_url(self):
        return reverse('entries:user_entries')
    
    def get_object(self, queryset=None):
        ref = self.kwargs.get('ref')
        return get_object_or_404(Entry, entry_ref=ref)

    def get_context_data(self, **kwargs):
        context = super(EntryDeleteView, self).get_context_data(**kwargs)
        context['action'] = 'delete'
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Your entry was deleted')
        return super(EntryDeleteView, self).delete(request, *args, **kwargs)


class EntryWithdrawView(LoginRequiredMixin, generic.UpdateView):
    """
    An update view for withdrawing from a category
    """
    model = Entry
    template_name = 'entries/delete_withdraw_entry.html'
    success_message = 'Your entry has been withdrawn'
    fields = ('id',)

    def get_object(self, queryset=None):
        ref = self.kwargs.get('ref')
        return get_object_or_404(Entry, entry_ref=ref)

    def get_context_data(self, **kwargs):
        context = super(EntryWithdrawView, self).get_context_data(**kwargs)
        context['action'] = 'withdraw'
        return context

    def form_valid(self, form):
        entry = form.save(commit=False)
        entry.withdrawn = True
        entry.save()

        messages.success(self.request, self.success_message)

        return HttpResponseRedirect(reverse('entries:user_entries'))


@login_required
def entry_video_payment(request, ref):
    entry = get_object_or_404(Entry, entry_ref=ref)
    template_name = 'entries/video_payment.html'

    context = {'entry': entry}

    if entry.video_entry_paid:
        context['already_paid'] = True
    elif entry.status == 'in_progress':
        context['in_progress'] = True
    elif entry.withdrawn:
        context['withdrawn'] = True
    else:
        host = 'http://{}'.format(request.META.get('HTTP_HOST'))
        invoice_id = create_entry_paypal_transaction(
            request.user, entry, 'video').invoice_id
        paypalform = PayPalPaymentsVideoForm(
            initial=get_paypal_dict(
                host,
                SELECTED_ENTRY_FEES[entry.category],
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
            'fee': SELECTED_ENTRY_FEES[entry.category]
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
