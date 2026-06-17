from tabulate import tabulate
from datetime import datetime, timedelta


"""
CLI interface for should-i-bike
"""


class CLI_Interface():

    def __init__(self, should_i_bike):
        """
        Initialize stuff
        """

        self.should_i_bike = should_i_bike

    def menuSelection(self, menuItems):
        """
        Displays menu items, waits for a valid choice
        """

        while True:
            for i in range(len(menuItems)):
                print(f"{i + 1}. {menuItems[i]}")

            try:
                selectNum = int(input("\nEnter the number of your choice: "))
            except ValueError:
                print("Please enter only numbers.")
                break

            try:
                selection = menuItems[selectNum - 1]
                print("Selected: ", selection)
                return selection
            except IndexError:
                print("Please choose a valid number.")

    def displayForecast(self, forecast):
        """
        Displays the forecast
        """

        table = [
            [
                "Time",
                "Temp",
                "Wind\nSpeed",
                "Wind\nDir.",
                "Wind\nGust",
                "Rain\nChance",
                "Visibility"
            ]
        ]

        for f in forecast:

            time = datetime.strptime(f['startTime'], '%Y-%m-%dT%H:%M:%S%z')

            timestring = time.strftime("%m-%d %-I%p")

            table.append([
                timestring,
                f['temperature'],
                f['windSpeed'],
                f['windDirection'],
                f"{f['windGust']} mph",
                f"{f['probabilityOfPrecipitation']['value']}%",
                f"{f['visibility']} yards"
            ])

        print(tabulate(table, headers='firstrow', tablefmt='fancy_grid'))

    def settingsMenu(self, settings):
        """
        Displays settings, with options to modify.
        """

        table = [["ID", "Setting", "Value", "Description"]]
        settingNames = []

        for setting in settings:
            table.append(setting)
            settingNames.append(setting[1])

        menuItems = ['Change a setting', 'Back to Main Menu']

        print(tabulate(table, headers='firstrow', tablefmt='fancy_grid'))

        # Settings menu loop
        while True:
            print('Settings Menu')
            selection = self.menuSelection(menuItems)

            if selection == 'Back to Main Menu':
                break
            if selection == 'Change a setting':
                print("\nSelect the setting you wish to change")
                settingName = self.menuSelection(settingNames)
                value = input("Enter the new value: ")
                self.should_i_bike.updateSetting(settingName, value)
                print("\nSetting has been updated.")
                break

    def displayRules(self, rules):
        """ Displays a table of rules """

        table = [["ID", "Name", "Trip Time", "Weight"]]

        for rule in rules:
            table.append(rule)

        print(tabulate(table, headers='firstrow', tablefmt='fancy_grid'))

    def selectID(self, ids, names=None):
        """
        Asks user to select an ID, makes sure it's valid.

        Accepts an array of IDS, and an optional array of names
        (if provided, both should be in the same order)
        """

        print(ids)

        if len(ids) < 1:
            print("No IDs to select.")
            return None

        while True:
            try:
                id = int(input("Enter the ID that you wish to select. "))
            except ValueError:
                print("Please enter only numbers.")

            if id in ids:
                return id
            else:
                print("That ID is not valid.")

    def displayRuleGroups(self, ruleGroups):
        """ Displays rule groups and elements """

        table = [[
            "Group ID",
            "Group Operator",
            "Element ID",
            "Type",
            "Operator",
            "Value"
        ]]

        for rg in ruleGroups:
            table.append([rg['id'], rg['operator']])

            for rge in rg['elements']:
                table.append(
                    [
                        "",
                        "",
                        rge['id'],
                        rge['type'],
                        rge['operator'],
                        rge['value']
                    ]
                )

        print(tabulate(table, headers='firstrow', tablefmt='fancy_grid'))

    def createRuleGroup(self, ruleID):
        """
        Collects info needed to create a new rule group
        """

        while True:
            operator = input(
                "Please enter AND for an AND grouping, "
                "or OR for an OR grouping. "
            )
            if (operator.upper() != "AND") and (operator.upper() != "OR"):
                print("Invalid input.")
            else:
                break

        ruleGroup = {
            "ruleID": ruleID,
            "operator": operator.upper()
        }

        return ruleGroup

    def createGroupElement(self, groupID, ruleTypes):
        """
        Gathers information necessary for creating a rule group element
        """

        operatorTypes = [
            "=",
            "!=",
            ">",
            ">=",
            "<=",
            "<",
            "CONTAINS",
            "NOT CONTAINS"
        ]

        print("Select rule type:")
        ruleType = self.menuSelection(ruleTypes)
        print("Select your operator:")
        operator = self.menuSelection(operatorTypes)
        value = input("Enter the value: ")

        groupElement = {
            "groupID": groupID,
            "ruleType": ruleType,
            "operator": operator,
            "value": value
        }

        return groupElement

    def createRule(self):
        """ Gathers info needed to create a rule. """

        tripTimeOptions = ["Departure", "Return"]

        name = input("Enter the name of the rule: ")
        print("Select the trip time:")
        tripTime = self.menuSelection(tripTimeOptions)

        while True:
            print("Assign a numerical weight for the rule.")
            try:
                weight = int(input(
                    "(Higher number have greater weight): "))
                break
            except ValueError:
                print("Please enter only numbers.")

        rule = {
            "name": name,
            "tripTime": tripTime,
            "weight": weight
        }

        return rule

    def selectDate(self):
        """ Allows the user to select a date. """

        tomorrow = datetime.now() + timedelta(days=1)
        tomorrow = tomorrow.strftime("%m/%d/%Y")
        prompt = ("Enter your travel date in mm/dd/yyyy format, or press Enter"
                  f" to select {tomorrow}: "
                  )

        while True:
            try:
                date = input(prompt)
                if date == "":
                    return tomorrow
                elif datetime.strptime(
                    date,
                    "%m/%d/%Y"
                ):
                    return date
            except ValueError:
                print("Date check failed.")

    def selectTravelTimes(self):
        """ Allows the user to select their travel times. """

        d = self.should_i_bike.defaultDeparture
        r = self.should_i_bike.defaultReturn
        print(f"Default departure: {d}, Default return: {r}")
        s = input("Press Enter to accept default times, "
                  "or anything else to enter custom times: ")
        if s == "":
            print("{:02d}".format(d), "{:02d}".format(r))
            return "{:02d}".format(d), "{:02d}".format(r)
        else:
            while True:
                try:
                    d = int(input("Enter departure time (0-24): "))
                    if (d >= 0) and (d <= 24):
                        break
                except ValueError:
                    print("Numbers only, please.")

            while True:
                try:
                    r = int(input("Enter return time (0-24): "))
                    if (d >= 0) and (d <= 24):
                        break
                except ValueError:
                    print("Numbers only, please.")
            return "{:02d}".format(d), "{:02d}".format(r)

    def displayShouldIBike(self, result):
        """
        Displays the result when Should I Bike is evaluated.

        The result object has the following elements:
        score (numeric)
        bike (True/False)
        relevenatRules [
            {
                name
                weight
                tripTime
            }
        ]
        """

        scoreboard = [["Should I Bike?", "Score"]]

        if result['bike'] is True:
            scoreboard.append(["Yes, you should bike."])
        else:
            scoreboard.append(["No, take the day off and drive."])

        scoreboard[1].append(result['score'])

        print("\n")
        print(tabulate(scoreboard, headers='firstrow', tablefmt='fancy_grid'))
        print("\n")

        print("Relevant Rules")

        ruleTable = [["Name", "Trip Time", "Weight"]]
        for rule in result['relevantRules']:
            ruleTable.append([
                rule['name'],
                rule['tripTime'],
                rule['weight']
            ])

        print(tabulate(ruleTable, headers='firstrow', tablefmt='fancy_grid'))
        print("\n")

    def displayTravelConditions(self, date, d, r):
        """
        Displays forecasted weather during the departure and return times.

        date is mm/dd/yyyy format
        d and r are times in 0-24 format
        """

        print('Travel Conditions')

        conditionTable = [[
            "Trip",
            "Temp",
            "Wind Speed",
            "Wind Dir.",
            "Wind Gust",
            "Rain Chance",
            "Visibility"
        ]]

        conditionTable.append([
            "Departure",
            self.should_i_bike.weather.getForecastValue(
                weatherElement="temperature",
                date=date,
                time=d
            ),
            self.should_i_bike.weather.getForecastValue(
                weatherElement="windSpeed",
                date=date,
                time=d
            ),
            self.should_i_bike.weather.getForecastValue(
                weatherElement="windDirection",
                date=date,
                time=d
            ),
            self.should_i_bike.weather.getForecastValue(
                weatherElement="windGust",
                date=date,
                time=d
            ),
            self.should_i_bike.weather.getForecastValue(
                weatherElement="probabilityOfPrecipitation",
                date=date,
                time=d
            ),
            self.should_i_bike.weather.getForecastValue(
                weatherElement="visibility",
                date=date,
                time=d
            )
        ])

        conditionTable.append([
            "Return",
            self.should_i_bike.weather.getForecastValue(
                weatherElement="temperature",
                date=date,
                time=r
            ),
            self.should_i_bike.weather.getForecastValue(
                weatherElement="windSpeed",
                date=date,
                time=r
            ),
            self.should_i_bike.weather.getForecastValue(
                weatherElement="windDirection",
                date=date,
                time=r
            ),
            self.should_i_bike.weather.getForecastValue(
                weatherElement="windGust",
                date=date,
                time=r
            ),
            self.should_i_bike.weather.getForecastValue(
                weatherElement="probabilityOfPrecipitation",
                date=date,
                time=r
            ),
            self.should_i_bike.weather.getForecastValue(
                weatherElement="visibility",
                date=date,
                time=r
            )
        ])

        print(tabulate(
            conditionTable,
            headers='firstrow',
            tablefmt='fancy_grid'
        ))
