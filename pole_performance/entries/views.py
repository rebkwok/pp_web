from django.conf import settings
from django.core.urlresolvers import reverse
from django.shortcuts import render
from django.views import generic

from braces.views import LoginRequiredMixin

from payments.forms import PayPalPaymentsListForm
from payments.models import create_entry_paypal_transaction

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
            if entry.status == 'submitted' and not entry.video_entry_paid:
                # ONLY DO THIS IF PAYPAL BUTTON NEEDED
                invoice_id = create_entry_paypal_transaction(
                    self.request.user, entry, 'video').invoice_id
                host = 'http://{}'.format(self.request.META.get('HTTP_HOST'))
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

            if entry.status == 'selected' and not entry.selected_entry_paid:
                # ONLY DO THIS IF PAYPAL BUTTON NEEDED
                invoice_id = create_entry_paypal_transaction(
                    self.request.user, entry, 'selected').invoice_id
                host = 'http://{}'.format(self.request.META.get('HTTP_HOST'))
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

            can_delete = True if entry.status == 'in_progress' else False

            entrydict = {
                'instance': entry,
                'paypal_video_form': paypal_video_form,
                'paypal_selected_form': paypal_selected_form,
                'can_delete': can_delete,
            }
            entries.append(entrydict)
        context['entries'] = entries
        return context


class EntryCreateView(LoginRequiredMixin, generic.CreateView):
    model = Entry


class EntryUpdateView(LoginRequiredMixin, generic.UpdateView):
    model = Entry


class EntryDeleteView(LoginRequiredMixin, generic.DeleteView):
    model = Entry
