from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, HttpResponseRedirect, render
from django.views import generic

from braces.views import LoginRequiredMixin

from payments.forms import PayPalPaymentsListForm
from payments.models import create_entry_paypal_transaction

from .forms import EntryCreateUpdateForm
from .models import Entry, ENTRY_FEES


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
        return Entry.objects.select_related('user')\
            .filter(user=self.request.user)

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
                            ENTRY_FEES[entry.category],  # TODO confirm fees for each stage
                            'Video submission fee',
                            invoice_id,
                            'video {}'.format(entry.id),
                            paypal_email=settings.DEFAULT_PAYPAL_EMAIL,
                        )
                    )

                if entry.status == 'selected' and not \
                        entry.selected_entry_paid:
                    # ONLY DO THIS IF PAYPAL BUTTON NEEDED
                    invoice_id = create_entry_paypal_transaction(
                        self.request.user, entry, 'selected').invoice_id
                    paypal_selected_form = PayPalPaymentsListForm(
                        initial=get_paypal_dict(
                            host,
                            ENTRY_FEES[entry.category],  # TODO confirm fees for each stage
                            'Entry fee',
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

        if self.request.POST.get('save', None):
            action = 'saved'
        elif self.request.POST.get('submit', None):
            action = 'submitted'

        if entry.status == 'in_progress' and 'submit' in self.request.POST:
            entry.status = 'submitted'
        entry.save()

        messages.success(self.request, self.success_message.format(action))

        return HttpResponseRedirect(self.get_success_url())

    def get_form_kwargs(self):
        kwargs = super(EntryMixin, self).get_form_kwargs()
        kwargs.update({'user': self.request.user})
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
