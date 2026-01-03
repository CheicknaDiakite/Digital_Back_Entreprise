# utils/role_restriction.py
from datetime import datetime

def is_user_allowed(user):
    try:
        r = user.rolerestriction
        if not r.active:
            return True

        now = datetime.now()
        day = now.weekday()  # 0 = lundi
        time = now.time()

        in_day = (
            r.day_start <= day <= r.day_end
            if r.day_start <= r.day_end
            else day >= r.day_start or day <= r.day_end
        )

        in_time = r.hour_start <= time <= r.hour_end

        return not (in_day and in_time)

    except:
        return True
