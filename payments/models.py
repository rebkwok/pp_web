# -*- coding: utf-8 -*-

import logging
import random

from django.db import models
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.template.loader import get_template

from paypal.standard.models import ST_PP_COMPLETED, ST_PP_REFUNDED, \
    ST_PP_PENDING
from paypal.standard.ipn.signals import valid_ipn_received, invalid_ipn_received

from entries.models import Entry

from activitylog.models import ActivityLog


logger = logging.getLogger(__name__)


def create_entry_paypal_transaction(user, entry, payment_type):
    id_string = "{}-{}-inv#".format(entry.entry_ref, payment_type)
    existing = PaypalEntryTransaction.objects.select_related('entry').filter(
        payment_type=payment_type,
        invoice_id__contains=id_string, entry=entry
    ).order_by('-invoice_id')

    if existing:
        # PaypalEntryTransaction is created when the view is called, not when
        # payment is made.  If there is no transaction id stored against it,
        # we shouldn't need to make a new one
        for transaction in existing:
            if not transaction.transaction_id:
                return transaction
        existing_counter = existing[0].invoice_id[-3:]
        counter = str(int(existing_counter) + 1).zfill(len(existing_counter))
    else:
        counter = '001'

    invoice_id = id_string + counter

    pbt = PaypalEntryTransaction.objects.create(
        invoice_id=invoice_id, entry=entry, payment_type=payment_type
    )
    return pbt


class PayPalTransactionError(Exception):
    pass


class PaypalEntryTransaction(models.Model):
    invoice_id = models.CharField(
        max_length=255, null=True, blank=True, unique=True
    )
    entry = models.ForeignKey(Entry, null=True)
    payment_type = models.CharField(
        choices=(
            ('video', 'video'),
            ('selected', 'selected'),
            ('withdrawal', 'withdrawal')
        ),
        max_length=255
    )
    transaction_id = models.CharField(
        max_length=255, null=True, blank=True, unique=True
    )

    def __str__(self):
        return self.invoice_id


def send_processed_payment_emails(
        payment_type_verbose, paypal_trans, user, obj, amount
):
    ctx = {
        'user': " ".join([user.first_name, user.last_name]),
        'payment_type': payment_type_verbose,
        'obj': obj,
        'invoice_id': paypal_trans.invoice_id,
        'paypal_transaction_id': paypal_trans.transaction_id,
        'paypal_email': settings.DEFAULT_PAYPAL_EMAIL,
        'fee': amount
    }

    # send email to user
    send_mail(
        '{} Payment processed for {} for entry ref {}'.format(
            settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, payment_type_verbose,
            obj.entry_ref
        ),
        get_template(
            'payments/email/payment_processed_to_user.txt').render(ctx),
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=get_template(
            'payments/email/payment_processed_to_user.html').render(ctx),
        fail_silently=False)


def send_processed_refund_emails(
        payment_type_verbose, paypal_trans, user, obj
):
    ctx = {
        'user': " ".join([user.first_name, user.last_name]),
        'payment_type': payment_type_verbose,
        'obj': obj,
        'invoice_id': paypal_trans.invoice_id,
        'paypal_transaction_id': paypal_trans.transaction_id,
        'paypal_email': settings.DEFAULT_PAYPAL_EMAIL
    }
    # send email to studio only and to support for checking;
    # user will have received automated paypal payment
    send_mail(
        '{} Payment refund processed for {} for entry ref {}'.format(
            settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, payment_type_verbose,
            obj.entry_ref),
        get_template(
            'payments/email/payment_refund_processed_to_studio.txt'
        ).render(ctx),
        settings.DEFAULT_FROM_EMAIL,
        [settings.SUPPORT_EMAIL],
        html_message=get_template(
            'payments/email/payment_refund_processed_to_studio.html'
        ).render(ctx),
        fail_silently=False)


def get_obj(ipn_obj):
    try:
        custom = ipn_obj.custom.split()
        payment_type = custom[0]
        entry_id = int(custom[1])
    except (IndexError, ValueError):
        # in case custom not included in paypal response or incorrect format
        raise PayPalTransactionError('Unknown object for payment')

    if payment_type not in ['video', 'selected', 'withdrawal']:
        raise PayPalTransactionError('Unknown payment type %s' % payment_type)

    try:
        obj = Entry.objects.select_related('user').get(id=entry_id)
    except Entry.DoesNotExist:
        raise PayPalTransactionError(
            'Entry with id {} does not exist'.format(entry_id)
        )

    paypal_trans = PaypalEntryTransaction.objects.filter(
        entry=obj, payment_type=payment_type
    )
    if not paypal_trans:
        paypal_trans = create_entry_paypal_transaction(
            user=obj.user, entry=obj, payment_type=payment_type
        )
    elif paypal_trans.count() > 1:
        # Unlikely we'll have 2 paypal trans created, since invoice_id is
        # created and retrieved using entry_ref which is randomly generated,
        # but just in case
        if ipn_obj.invoice:
            paypal_trans = PaypalEntryTransaction\
                .objects.select_related('entry').get(
                entry=obj, invoice_id=ipn_obj.invoice,
                payment_type=payment_type
            )
        else:
            paypal_trans = paypal_trans.latest('id')
    else:  # we got one paypaltrans, as we should have
        paypal_trans = paypal_trans[0]

    payment_type_verbose = {
        'video': 'video submission fee',
        'selected': 'selected entry fee',
        'withdrawal': 'withdrawal fee'
    }
    return {
        'payment_type': payment_type,
        'payment_type_verbose': payment_type_verbose[payment_type],
        'obj': obj,
        'paypal_trans': paypal_trans,
    }


def payment_received(sender, **kwargs):
    ipn_obj = sender

    try:
        obj_dict = get_obj(ipn_obj)
    except PayPalTransactionError as e:
        send_mail(
        'WARNING! Error processing PayPal IPN',
        'Valid Payment Notification received from PayPal but an error '
        'occurred during processing.\n\nTransaction id {}\n\nThe flag info '
        'was "{}"\n\nError raised: {}'.format(
            ipn_obj.txn_id, ipn_obj.flag_info, e
        ),
        settings.DEFAULT_FROM_EMAIL, [settings.SUPPORT_EMAIL],
        fail_silently=False)
        logger.error(
            'PaypalTransactionError: unknown object type for payment '
            '(ipn_obj transaction_id: {}, error: {})'.format(
                ipn_obj.txn_id, e
            )
        )
        return

    obj = obj_dict['obj']
    payment_type = obj_dict['payment_type']
    payment_type_verbose = obj_dict['payment_type_verbose']
    paypal_trans = obj_dict['paypal_trans']

    try:
        if ipn_obj.business != settings.DEFAULT_PAYPAL_EMAIL:
            ipn_obj.set_flag(
                "Invalid receiver_email (%s)" % ipn_obj.business
            )
            ipn_obj.save()
            raise PayPalTransactionError(ipn_obj.flag_info)

        if ipn_obj.payment_status == ST_PP_REFUNDED:
            if payment_type == 'video':
                obj.video_entry_paid = False
            elif payment_type == 'selected':
                obj.selected_entry_paid = False
            elif payment_type == 'withdrawal':
                obj.withdrawal_fee_paid = False
            obj.save()

            ActivityLog.objects.create(
                log='{} for entry id {} for user {} has been refunded '
                    'from paypal; paypal transaction id {}, '
                    'invoice id {}.'.format(
                        payment_type_verbose, obj.id, obj.user.username,
                        ipn_obj.txn_id, paypal_trans.invoice_id
                    )
            )
            send_processed_refund_emails(
                payment_type_verbose, paypal_trans, obj.user, obj
            )

        elif ipn_obj.payment_status == ST_PP_PENDING:
            ActivityLog.objects.create(
                log='PayPal payment returned with status PENDING for {} '
                    'for entry {}; ipn obj id {} (txn id {})'.format(
                     payment_type_verbose, obj.id, ipn_obj.id, ipn_obj.txn_id
                    )
            )
            raise PayPalTransactionError(
                'PayPal payment returned with status PENDING for {} '
                'for entry {}; '
                'ipn obj id {} (txn id {}).  This is usually due to an '
                'unrecognised or unverified paypal email address.'.format(
                    payment_type_verbose, obj.id, ipn_obj.id, ipn_obj.txn_id
                )
            )

        elif ipn_obj.payment_status == ST_PP_COMPLETED:
            # we only process if payment status is completed
            # check for django-paypal flags (checks for valid payment status,
            # duplicate trans id, correct receiver email, valid secret (if using
            # encrypted), mc_gross, mc_currency, item_name and item_number are all
            # correct
            if payment_type == 'video':
                obj.video_entry_paid = True
            elif payment_type == 'selected':
                obj.selected_entry_paid = True
            elif payment_type == 'withdrawal':
                obj.withdrawal_fee_paid = True
            obj.save()

            # do this AFTER saving the entry as paid; in the edge case that a
            # user re-requests the page with the paypal button on it in between
            # entering and the paypal transaction being saved, this prevents a
            # second invoice number being generated
            paypal_trans.transaction_id = ipn_obj.txn_id
            paypal_trans.save()

            ActivityLog.objects.create(
                log='{} for entry id {} for user {} paid by PayPal; paypal '
                    'id {}'.format(
                    payment_type_verbose.title(), obj.id, obj.user.username,
                    paypal_trans.id
                    )
            )
            send_processed_payment_emails(
                payment_type_verbose, paypal_trans, obj.user, obj,
                str(ipn_obj.mc_gross)
            )

            if not ipn_obj.invoice:
                # sometimes paypal doesn't send back the invoice id -
                # everything should be ok but email to check
                ipn_obj.invoice = paypal_trans.invoice_id
                ipn_obj.save()
                send_mail(
                    '{} No invoice number on paypal ipn for '
                    '{} for entry id {}'.format(
                        settings.ACCOUNT_EMAIL_SUBJECT_PREFIX,
                        payment_type_verbose, obj.id
                    ),
                    'Please check entry and paypal records for '
                    'paypal transaction id {}.  No invoice number on paypal'
                    ' IPN.  Invoice number has been set to {}.'.format(
                        ipn_obj.txn_id, paypal_trans.invoice_id
                    ),
                    settings.DEFAULT_FROM_EMAIL,
                    [settings.SUPPORT_EMAIL],
                    fail_silently=False
                )

        else:  # any other status
            ActivityLog.objects.create(
                log='Unexpected payment status {} for {} for entry {}; '
                    'ipn obj id {} (txn id {})'.format(
                    ipn_obj.payment_status.upper(), payment_type_verbose,
                    obj.id, ipn_obj.id, ipn_obj.txn_id
                    )
            )
            raise PayPalTransactionError(
                'Unexpected payment status {} for {} for entry {}; '
                'ipn obj id {} (txn id {})'.format(
                    ipn_obj.payment_status.upper(), payment_type_verbose,
                    obj.id, ipn_obj.id, ipn_obj.txn_id
                )
            )

    except Exception as e:
        # if anything else goes wrong, send a warning email
        logger.warning(
            'Problem processing payment for {} for entry {}; '
            'invoice_id {}, transaction id: {}.  Exception: {}'.format(
                payment_type_verbose, obj.id, ipn_obj.invoice,
                ipn_obj.txn_id, e
                )
        )

        send_mail(
            '{} There was some problem processing {} for '
            'entry id {}'.format(
                settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, payment_type_verbose,
                obj.id
            ),
            'Please check your entry and paypal records for '
            'invoice # {}, paypal transaction id {}.\n\nThe exception '
            'raised was "{}"'.format(
                ipn_obj.invoice, ipn_obj.txn_id, e
            ),
            settings.DEFAULT_FROM_EMAIL,
            [settings.SUPPORT_EMAIL],
            fail_silently=False)


def payment_not_received(sender, **kwargs):
    ipn_obj = sender

    try:
        obj_dict = get_obj(ipn_obj)
    except PayPalTransactionError as e:
        send_mail(
            'WARNING! Error processing Invalid Payment Notification from PayPal',
            'PayPal sent an invalid transaction notification while '
            'attempting to process payment;.\n\nThe flag '
            'info was "{}"\n\nAn additional error was raised: {}'.format(
                ipn_obj.flag_info, e
            ),
            settings.DEFAULT_FROM_EMAIL, [settings.SUPPORT_EMAIL],
            fail_silently=False)
        logger.error(
            'PaypalTransactionError: unknown object type for payment ('
            'transaction_id: {}, error: {})'.format(ipn_obj.txn_id, e)
        )
        return

    try:
        obj = obj_dict.get('obj')
        payment_type = obj_dict.get('payment_type')
        payment_type_verbose = obj_dict.get('payment_type_verbose')

        if obj:
            logger.warning('Invalid Payment Notification received from PayPal '
                           'for {} for entry id {}'.format(
                    payment_type_verbose, obj.id
                )
            )
            send_mail(
                'WARNING! Invalid Payment Notification received from PayPal',
                'PayPal sent an invalid transaction notification while '
                'attempting to process {} for entry id {}.\n\nThe flag '
                'info was "{}"'.format(
                    payment_type_verbose, obj.id, ipn_obj.flag_info
                ),
                settings.DEFAULT_FROM_EMAIL, [settings.SUPPORT_EMAIL],
                fail_silently=False)

    except Exception as e:
            # if anything else goes wrong, send a warning email
            logger.warning(
                'Problem processing payment_not_received for {} for '
                'entry id {}; invoice_id {}, transaction id: {}. '
                'Exception: {}'.format(
                    payment_type_verbose, obj.id, ipn_obj.invoice,
                    ipn_obj.txn_id, e
                )
            )
            send_mail(
                '{} There was some problem processing payment_not_received for '
                '{} payment for entry id {}'.format(
                    settings.ACCOUNT_EMAIL_SUBJECT_PREFIX,
                    payment_type_verbose, obj.id
                ),
                'Please check your entry and paypal records for '
                'invoice # {}, paypal transaction id {}.\n\nThe exception '
                'raised was "{}".\n\nNOTE: this error occurred during '
                'processing of the payment_not_received signal'.format(
                    ipn_obj.invoice, ipn_obj.txn_id, e
                ),
                settings.DEFAULT_FROM_EMAIL,
                [settings.SUPPORT_EMAIL],
                fail_silently=False)

valid_ipn_received.connect(payment_received)
invalid_ipn_received.connect(payment_not_received)
