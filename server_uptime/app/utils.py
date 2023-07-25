import pytz


def localize_datetime(datetime_obj, tz):
    """Localizes a given datetime object to the specified timezone."""
    local_tz = pytz.timezone(tz)
    localized_time = local_tz.localize(datetime_obj)
    return localized_time
