from django.conf import settings
from django.core.mail import send_mail
from django.core.mail.message import EmailMultiAlternatives
from django.template.loader import get_template

from activitylog.models import ActivityLog


def send_pp_email(
        request,
        subject, ctx, template_txt, template_html,
        prefix=settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, to_list=[],
        from_email=settings.DEFAULT_FROM_EMAIL, cc_list=[],
        bcc_list=[], reply_to_list=[settings.DEFAULT_STUDIO_EMAIL]
):
    host = 'http://{}'.format(request.META.get('HTTP_HOST'))
    ctx.update({'host': host})
    try:
        msg = EmailMultiAlternatives(
            '{} {}'.format(prefix, subject),
            get_template(
                template_txt).render(
                    ctx
                ),
            from_email=from_email,
            to=to_list,
            bcc=bcc_list,
            cc=cc_list,
            reply_to=reply_to_list
            )
        msg.attach_alternative(
            get_template(
                template_html).render(
                  ctx
              ),
            "text/html"
        )
        msg.send(fail_silently=False)
        return 'OK'

    except Exception as e:
        # send mail to tech support with Exception
        send_support_email(e, __name__)


def send_support_email(e, module_name=""):
    try:
        send_mail('{} An error occurred!'.format(
                settings.ACCOUNT_EMAIL_SUBJECT_PREFIX
            ),
            'An error occurred in {}\n\nThe exception '
            'raised was "{}"'.format(module_name, e),
            settings.DEFAULT_FROM_EMAIL,
            [settings.SUPPORT_EMAIL],
            fail_silently=True)
    except Exception as ex:
        ActivityLog.objects.create(
            log="Problem sending an email ({}: {})".format(
                module_name, ex
            )
        )
