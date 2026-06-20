from noaa_sdk import NOAA
from datetime import datetime, timedelta
import re

"""
Handles weather calls and information
"""


class Weather():

    def __init__(self, should_i_bike, date='03/22/2023'):
        """
        More here later
        """

        self.should_i_bike = should_i_bike

        self.lastRefreshTime = datetime(1990, 1, 1)
        self.forecast = []
        self.noaa = NOAA()
        self.noaa.user_agent = 'should-i-bike'

        # Create dictionary of conversion methods
        self.conversions = {
            "wmoUnit:degC": self.convertTemp,
            "wmoUnit:degree_(angle)": self.convertAngleToDir,
            "wmoUnit:km_h-1": self.convertKMtoMiles,
            "wmoUnit:m": self.convertMtoYards
        }

    def convertTemp(self, temp=0.0):
        """
        Accepts a celcius temperature and converts it to farenheit
        """

        f = (temp * 9/5) + 32
        return f

    def convertKMtoMiles(self, km=0.0):
        """ Converts KM to Miles """

        d = km * 0.62137
        return int(round(d, 0))

    def convertMtoYards(self, m=0.0):
        """ Converts meters to yards. """

        d = m * 1.0936132983377
        return (int(round(d, 0)))

    def convertAngleToDir(self, angle=0.0):
        """ Converts an angle to a cardinal direction. """

        directions = [
            (0, "N"),
            (22.5, "NNE"),
            (45, "NE"),
            (67.5, "ENE"),
            (90, "E"),
            (112.5, "ESE"),
            (135, "SE"),
            (157.5, "SSE"),
            (180, "S"),
            (202.5, "SSW"),
            (225, "SW"),
            (247.5, "WSW"),
            (270, "W"),
            (292.5, "WNW"),
            (315, "NW"),
            (337.5, "NNW")
        ]

        dir = [x for x in directions
               if x[0] <= angle]

        return dir[-1][1]

    def getWeather(self):
        """
        Gets the upcoming weather forecast

        We may need to add something here to handle 500 (and other) errors
        from NOAA
        """

        # Get updated forecast if it's more than an hour old
        minutes_diff = (
            datetime.now() - self.lastRefreshTime
            ).total_seconds() / 60.0
        if minutes_diff > 60:
            print("Refreshing weather data...")

            # Get the hourly forecast
            self.forecastHourly = self.noaa.get_forecasts(
                self.should_i_bike.zip,
                self.should_i_bike.country,
                type='forecastHourly'
            )

            # Get the grid forecast for extra detail
            self.forecastGridData = self.noaa.get_forecasts(
                self.should_i_bike.zip,
                self.should_i_bike.country,
                type='forecastGridData'
            )

            # Add grid elements to the hourly forecast
            self.addGridElementToHourly(
                'windGust',
                self.forecastHourly,
                self.forecastGridData,
                conversionFunc=self.convertKMtoMiles
            )
            self.addGridElementToHourly(
                'visibility',
                self.forecastHourly,
                self.forecastGridData,
                conversionFunc=self.convertMtoYards
            )

            self.forecast = self.forecastHourly[
                :self.should_i_bike.hoursReturned]
            self.lastRefreshTime = datetime.now()

        return self.forecast

    def addGridElementToHourly(
            self,
            element,
            forecastHourly,
            forecastGridData,
            conversionFunc=None):
        """
        Grabs an element from the forecast grid data
        and adds it to the hourly forecast data.

        If the element needs to be converted (mile to KM or F to C),
        pass the conversion function as conversionFunc.
        """

        # Get the first timestamp in the hourly forecast
        firstHourly = datetime.strptime(
            forecastHourly[0]['startTime'],
            '%Y-%m-%dT%H:%M:%S%z'
        )

        # Match the timestamps in the Grid data.
        # The [:25] strips off the '/PT1H' ending at the end
        # of the validTime string since datetime doesn't
        # know what to do with that.
        values = forecastGridData[element]['values']

        # Add a datetime-formatted date to the element array
        # Also fill in any time gaps where there aren't
        # entries, using /PTxH as a guide.
        i = -1
        for value in values:
            i += 1
            # Add a python datetime element from the validTime
            ct = datetime.strptime(
                values[i]['validTime'][:25],
                '%Y-%m-%dT%H:%M:%S%z'
            )
            values[i]['convertedTime'] = ct

            # Check how many hours this value lasts
            rx = re.search(r"/PT([0-9]+)H", values[i]['validTime'])
            if rx:
                duration = rx.group(1)
            else:
                rx = re.search(
                    r"/P([0-9]+)DT([0-9]+)H",
                    values[i]['validTime']
                )
                days = int(rx.group(1))
                hours = int(rx.group(2))
                duration = (days * 24) + hours

            # Add extra entries if duration is longer than 1 hr
            # so that every hour will have an entry
            for d in range(int(duration) - 1):
                newCt = ct + timedelta(hours=d+1)
                newValidTime = '{:%Y-%m-%d}T{:%H:%M:%S}+00:00/PT1H'.format(
                    newCt,
                    newCt
                )
                newEntry = {
                    "validTime": newValidTime,
                    "value": values[i]['value']
                }

                values.insert(i+d+1, newEntry)

        # Find the temp entry that matches our first hourly record
        matchTime = [x for x in values
                     if x['convertedTime'] == firstHourly]

        # Get the index of the match
        valueIndex = values.index(matchTime[0])

        # Insert the grid elements into the hourly forecast
        for i in range(self.should_i_bike.hoursReturned):
            try:
                gridElement = values[i+valueIndex]['value']
            except IndexError:
                gridElement = values[-1]['value']

            # Convert the value if needed
            if conversionFunc:
                gridElement = conversionFunc(gridElement)

            forecastHourly[i][element] = gridElement

    def getForecastValue(self, weatherElement, date, time):
        """
        Returns a value for a specified weather element at a
        specified time.

        Time is an hour in 24-hour time (0-24)
        """

        tz_raw = datetime.now().astimezone().strftime('%z')
        tz_str = tz_raw[:3] + ':' + tz_raw[3:]
        targetTime = datetime.strptime(
            date+'T'+str(time)+tz_str,
            '%m/%d/%YT%H%z'
        )

        # Make sure weather data is up to date
        self.getWeather()

        # Grab all entries for this element prior to the requested time
        entries = [x for x in self.forecastGridData[weatherElement]['values']
                   if datetime.strptime(
                    x['validTime'][:25],
                    '%Y-%m-%dT%H:%M:%S%z') <= targetTime
                   ]
        # print("\nValid Time", entries[-1]['validTime'])
        # print("Unconverted Value:", entries[-1]['value'])
        # print(
        #     "Unit of measurement:",
        #     self.forecastGridData[weatherElement]['uom']
        # )
        uom = self.forecastGridData[weatherElement]['uom']
        forecastValue = entries[-1]['value']
        if self.conversions.get(uom):
            forecastValue = self.conversions[uom](entries[-1]['value'])
            # print(f"Converted: {forecastValue}")

        return forecastValue
