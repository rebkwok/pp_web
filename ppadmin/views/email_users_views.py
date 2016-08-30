import ast
import logging

from math import ceil

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User

from django.contrib import messages
from django.core.urlresolvers import reverse
from django.template.response import TemplateResponse
from django.shortcuts import HttpResponseRedirect
from django.utils.safestring import mark_safe

from entries.email_helpers import send_pp_email

from ..forms.email_users_forms import EmailUsersForm
from ..views.helpers import staff_required

from activitylog.models import ActivityLog


logger = logging.getLogger(__name__)


@login_required
@staff_required
def email_users_view(
        request, mailing_list=False,
        template_name='ppadmin/email_users_form.html'
):
    if 'users_to_email' in request.POST:  # posting a test email; already in
        # dict form
        users_to_email = ast.literal_eval(request.POST.get('users_to_email'))
    else:
        users = []
        if mailing_list:
            subscribed, _ = Group.objects.get_or_create(name='subscribed')
            users = subscribed.user_set.all()
        if 'email_selected' in request.POST:
            users = User.objects.filter(id__in=request.POST.getlist('emailusers'))
        users_to_email = [
            {
                'id': user.id,
                'email': user.email,
                'fullname': '{} {} ({})'.format(
                    user.first_name, user.last_name, user.username
                )
            } for user in users
        ]

    if request.method == 'POST':
        if 'email_selected' in request.POST:
            form = EmailUsersForm()
        else:
            form = EmailUsersForm(request.POST)
            test_email = request.POST.get('send_test', False)

            if form.is_valid():
                prefix = ''
                subject = '{}{}'.format(
                    form.cleaned_data['subject'],
                    ' [TEST EMAIL]' if test_email else ''
                )
                from_address = form.cleaned_data['from_address']
                message = form.cleaned_data['message']
                cc = form.cleaned_data['cc']

                # bcc recipients
                email_addresses = [user['email'] for user in users_to_email]
                email_count = len(email_addresses)
                number_of_emails = ceil(email_count / 99)

                if test_email:
                    email_lists = [[from_address]]
                else:
                    email_lists = [email_addresses]  # will be a list of lists
                    # split into multiple emails of 99 bcc plus 1 cc
                    if email_count > 99:
                        email_lists = [
                            email_addresses[i : i + 99]
                            for i in range(0, email_count, 99)
                            ]

                for i, email_list in enumerate(email_lists):
                    sent_ok = True
                    ctx = {
                              'subject': subject,
                              'message': message,
                              'number_of_emails': number_of_emails,
                              'email_count': email_count,
                              'is_test': test_email,
                              'mailing_list': mailing_list,
                          }

                    sent = send_pp_email(
                        request, subject, ctx,
                        'ppadmin/email/email_users.txt',
                        'ppadmin/email/email_users.html',
                        prefix=None,
                        bcc_list=email_list,
                        cc_list=[from_address] if i == 0 and not
                        test_email else [],
                        from_email=from_address,
                        reply_to_list=[from_address]
                    )

                    if sent != 'OK':
                        sent_ok = False

                    if not test_email and sent_ok:
                        ActivityLog.objects.create(
                            log='{} email with subject "{}" sent to users '
                                '{} by admin user {}'.format(
                                'Mailing list' if mailing_list else 'Bulk',
                                subject, ', '.join(email_list),
                                request.user.username
                                )
                        )
                    if not sent_ok:
                        ActivityLog.objects.create(
                            log='There was a problem with at least one '
                                'email in the {} email with '
                                'subject "{}"'.format(
                                'Mailing list' if mailing_list else
                                'Bulk', subject, ', '.join(email_list),
                                request.user.username
                            )
                        )

                if not test_email and sent_ok:
                    messages.success(
                        request,
                        '{} email with subject "{}" has been sent to '
                        'users'.format(
                            'Mailing list' if mailing_list else 'Bulk',
                            subject
                        )
                    )
                    if mailing_list:
                        return HttpResponseRedirect(
                            reverse('ppadmin:mailing_list')
                            )
                    return HttpResponseRedirect(reverse('ppadmin:entries'))
                else:
                    messages.success(
                        request, 'Test email has been sent to {} only. Click '
                                 '"Send Email" below to send this email to '
                                 'users.'.format(
                                    from_address
                                    )
                    )

            if form.errors:
                messages.error(
                    request,
                    mark_safe(
                        "Please correct errors in form: {}".format(form.errors)
                    )
                )
            form = EmailUsersForm(request.POST)
    else:
        form = EmailUsersForm()

    return TemplateResponse(
        request, template_name, {
            'form': form,
            'users_to_email': users_to_email,
            'mailing_list': mailing_list
        }
    )
