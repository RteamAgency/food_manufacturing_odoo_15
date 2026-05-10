import datetime
import pytz
import tzlocal
from odoo import api, SUPERUSER_ID

def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    cron = env.ref('aznut_mrp.ir_cron_pause_workorders', raise_if_not_found=False)
    if not cron:
        return
    server_tz = tzlocal.get_localzone()
    server_now = datetime.datetime.now(server_tz)
    gmt4_tz = pytz.timezone('Etc/GMT+4')
    now_in_gmt4 = server_now.astimezone(gmt4_tz)
    target_gmt4 = now_in_gmt4.replace(hour=16, minute=0, second=0, microsecond=0)
    if now_in_gmt4 >= target_gmt4:
        target_gmt4 += datetime.timedelta(days=1)
    target_utc = target_gmt4.astimezone(pytz.utc)
    cron.write({
        'nextcall': target_utc.strftime('%Y-%m-%d %H:%M:%S')
    })
