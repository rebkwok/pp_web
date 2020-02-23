# -*- coding: utf-8 -*-

from django.conf import settings
from django.shortcuts import render
from django.template.response import TemplateResponse
from django.views.decorators.csrf import csrf_exempt

from paypal.standard.ipn.models import PayPalIPN

from entries.models import Entry

"""
def view_that_asks_for_money(request):

    # What you want the button to do.
    paypal_dict = {
        "business": settings.DEFAULT_PAYPAL_EMAIL,
        "amount": "10.00",
        "item_name": "Video submission fee for Beginner category",
        "invoice": "unique-invoice-id",
        "currency_code": "GBP",
        "notify_url": reverse('paypal-ipn'),
        "return_url": reverse('payments:paypal_confirm'),
        "cancel_return": reverse('payments:paypal_cancel'),

    }

    # Create the instance.
    form = PayPalPaymentsForm(initial=paypal_dict)
    context = {"form": form}
    return render("payment.html", context)
"""

@csrf_exempt
def paypal_confirm_return(request):
    obj = 'unknown'
    test_ipn_complete = False
    custom = request.POST.get('custom', '').split()

    if custom:
        try:
            payment_type = custom[0]  # video, selected or withdrawal payment
            entry_id = int(custom[1])
            obj = Entry.objects.select_related('user').get(id=entry_id)

            # Possible payment statuses:
            # Canceled_, Reversal, Completed, Denied, Expired, Failed, Pending,
            # Processed, Refunded, Reversed, Voided
            # NOTE: We can check for completed payment status for displaying
            # information in the template, but we can only confirm payment if the
            # booking or block has already been set to paid (i.e. the post from
            # paypal has been successfully processed
            context = {'obj': obj,
                       'payment_type': payment_type,
                       'payment_status': request.POST.get('payment_status'),
                       'purchase': request.POST.get('item_name'),
                       'sender_email': settings.DEFAULT_FROM_EMAIL,
                       'organiser_email': settings.DEFAULT_STUDIO_EMAIL,
                       }
        except IndexError:
            obj = 'unknown'

    if not custom or obj == 'unknown':
        context = {
            'obj_unknown': True,
            'organiser_email': settings.DEFAULT_STUDIO_EMAIL
        }
    return TemplateResponse(
        request, 'payments/confirmed_payment.html', context
    )


@csrf_exempt
def paypal_cancel_return(request):
    return render(request, 'payments/cancelled_payment.html')

