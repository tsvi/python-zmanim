from noaa_calculator import NOAACalculator
from geo_location import GeoLocation
from datetime import date, datetime, timedelta
import pytz
from astronomical_calculations import AstronomicalCalculations
from math_helper import MathHelper


class AstronomicalCalendar(MathHelper):
    GEOMETRIC_ZENITH = 90
    CIVIL_ZENITH = 96
    NAUTICAL_ZENITH = 102
    ASTRONOMICAL_ZENITH = 108

    __sentinel=object()

    def __init__(self, geo_location: GeoLocation = None, date: date = None, calculator: AstronomicalCalculations = None):
        if geo_location is None:
            geo_location = GeoLocation.GMT()
        if date is None:
            date = datetime.today()
        if calculator is None:
            calculator = NOAACalculator()
        self.geo_location = geo_location
        self.date = date
        self.astronomical_calculator = calculator

    def sunrise(self) -> datetime:
        return self.__date_time_from_time_of_day(self.utc_sunrise(self.GEOMETRIC_ZENITH), 'sunrise')

    def sea_level_sunrise(self) -> datetime:
        return self.sunrise_offset_by_degrees(self.GEOMETRIC_ZENITH)

    def sunrise_offset_by_degrees(self, offset_zenith: float) -> datetime:
        return self.__date_time_from_time_of_day(self.utc_sea_level_sunrise(offset_zenith), 'sunrise')

    def sunset(self) -> datetime:
        return self.__date_time_from_time_of_day(self.utc_sunset(self.GEOMETRIC_ZENITH), 'sunset')

    def sea_level_sunset(self) -> datetime:
        return self.sunset_offset_by_degrees(self.GEOMETRIC_ZENITH)

    def sunset_offset_by_degrees(self, offset_zenith: float) -> datetime:
        return self.__date_time_from_time_of_day(self.utc_sea_level_sunset(offset_zenith), 'sunset')

    def utc_sunrise(self, zenith: float) -> float:
        return self.astronomical_calculator.utc_sunrise(self.__adjusted_date(), self.geo_location, zenith, adjust_for_elevation=True)

    def utc_sea_level_sunrise(self, zenith: float) -> float:
        return self.astronomical_calculator.utc_sunrise(self.__adjusted_date(), self.geo_location, zenith, adjust_for_elevation=False)

    def utc_sunset(self, zenith: float) -> float:
        return self.astronomical_calculator.utc_sunset(self.__adjusted_date(), self.geo_location, zenith, adjust_for_elevation=True)

    def utc_sea_level_sunset(self, zenith: float) -> float:
        return self.astronomical_calculator.utc_sunset(self.__adjusted_date(), self.geo_location, zenith, adjust_for_elevation=False)

    def temporal_hour(self, sunrise: datetime = __sentinel, sunset: datetime = __sentinel) -> float:
        if sunrise == self.__sentinel:
            sunrise = self.sea_level_sunrise()
        if sunset == self.__sentinel:
            sunset = self.sea_level_sunset()

        if sunset is None or sunrise is None:
            return None

        daytime_hours = float((sunset - sunrise).total_seconds() / 3600.0)
        return (daytime_hours / 12) * self.HOUR_MILLIS

    def sun_transit(self) -> datetime:
        sunrise = self.sea_level_sunrise()
        sunset = self.sea_level_sunset()
        if sunrise is None or sunset is None:
            return None
        noon_hour = (self.temporal_hour(sunrise, sunset) / self.HOUR_MILLIS) * 6.0
        return sunrise + timedelta(noon_hour / 24.0)

    def __date_time_from_time_of_day(self, time_of_day: float, mode: str) -> datetime:
        if time_of_day is None:
            return None

        hours, remainder = divmod(time_of_day * 3600, 3600)
        minutes, remainder = divmod(remainder, 60)
        seconds, microseconds = divmod(remainder * 10**6, 10**6)
        adjusted_date = self.__adjusted_date()
        year, month, day = adjusted_date.year, adjusted_date.month, adjusted_date.day
        utc_time = datetime(year, month, day, int(hours), int(minutes), int(seconds), int(microseconds), tzinfo=pytz.UTC)

        # adjust date if utc time reflects a wraparound from the local offset
        local_offset = (self.geo_location.local_mean_time_offset() + self.geo_location.standard_time_offset()) / self.HOUR_MILLIS
        if hours + local_offset > 18 and mode == 'sunrise':  # sunrise after 6pm indicates the UTC date has occurred earlier
            utc_time -= timedelta(1)
        elif hours + local_offset < 6 and mode == 'sunset':  # sunset before 6am indicates the UTC date has occurred later
            utc_time += timedelta(1)

        return self.__convert_date_time_for_zone(utc_time)

    def __adjusted_date(self) -> date:
        return self.date + timedelta(days=self.geo_location.antimeridian_adjustment())

    def __convert_date_time_for_zone(self, utc_time: datetime) -> datetime:
        return utc_time.astimezone(self.geo_location.time_zone)
