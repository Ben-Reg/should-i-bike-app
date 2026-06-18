from cli_interface import CLI_Interface
from weather import Weather
from db import DB

"""
Checks the weather, then uses a set of user-defined rules to
decide whether the user should drive or ride their bike
"""


class Should_I_Bike:
    """ Overall class to manage program and behavior """

    def __init__(self):
        """Initialize program, create resources """

        # Using the CLI interface for now
        self.interface = CLI_Interface(self)
        self.weather = Weather(self)
        self.db = DB(self)

        # Load settings from the DB
        self.settings = self.db.loadSettings()

        self.programLoop = True

        self.menuItems = [
            "Should I Bike?",
            "Forecast",
            "Rules",
            "Settings",
            "Quit"
        ]

    @property
    def zip(self):
        if self.settings['Zip']['value']:
            return self.settings['Zip']['value']
        else:
            return '67114'

    @zip.setter
    def zip(self, value):
        self.db.updateSetting('Zip', value)
        self.settings = self.db.loadSettings()

    @property
    def country(self):
        if self.settings['Country']['value']:
            return self.settings['Country']['value']
        else:
            return 'US'

    @country.setter
    def country(self, value):
        self.db.updateSetting('Country', value)
        self.settings = self.db.loadSettings()

    @property
    def hoursReturned(self):
        if self.settings['Hours Returned']['value']:
            return int(self.settings['Hours Returned']['value'])
        else:
            return 48

    @hoursReturned.setter
    def hoursReturned(self, value):
        self.db.updateSetting('Hours Returned', value)

    @property
    def defaultDeparture(self):
        if self.settings['Default Departure']['value']:
            return int(self.settings['Default Departure']['value'])
        else:
            return 7

    @defaultDeparture.setter
    def default_departure(self, value):
        self.db.updateSetting('Default Departure', value)

    @property
    def defaultReturn(self):
        if self.settings['Default Return']['value']:
            return int(self.settings['Default Return']['value'])
        else:
            return 17

    @defaultReturn.setter
    def default_return(self, value):
        self.db.updateSetting('Default Return', value)

    def runProgram(self):
        """ Runs the program """
        while self.programLoop:

            self.selection = self.interface.menuSelection(self.menuItems)

            if self.selection == "Quit":
                self.programLoop = False
            elif self.selection == "Forecast":
                forecast = self.weather.getWeather()
                self.interface.displayForecast(forecast)
            elif self.selection == "Settings":
                self.interface.settingsMenu(self.db.loadSettings(type='array'))
            elif self.selection == "Rules":
                self.manageRules()
            elif self.selection == "Should I Bike?":
                date = self.interface.selectDate()
                d, r = self.interface.selectTravelTimes()
                result = self.evaluateRules(date, d, r)
                self.interface.displayShouldIBike(result)
                self.interface.displayTravelConditions(date, d, r)

    def updateSetting(self, settingName, value):
        """
        Changes a setting by the name.
        """

        self.db.updateSetting(settingName, value)
        self.settings = self.db.loadSettings()

    def manageRules(self):
        """
        Displays rules, with option to create, edit, delete.
        """

        ruleLoop = True

        while ruleLoop:
            # Display rules
            rules = self.db.loadRules()
            ruleIDs = []
            for rule in rules:
                ruleIDs.append(rule[0])

            self.interface.displayRules(rules)

            # Display rule menu
            ruleMenu = [
                "Create Rule",
                "Edit Rule (name, time, weight)",
                "Edit Rule Groupings and Elements",
                "Delete Rule",
                "Export Rules",
                "Import Rules",
                "Back"
            ]
            menuSelection = self.interface.menuSelection(ruleMenu)

            if menuSelection == "Back":
                ruleLoop = False
            elif menuSelection == "Edit Rule (name, time, weight)":
                ruleID = self.interface.selectID(ruleIDs)
                rule = self.interface.createRule()
                self.db.editRule(ruleID, rule)
            elif menuSelection == "Edit Rule Groupings and Elements":
                ruleID = self.interface.selectID(ruleIDs)
                self.manageRuleGroups(ruleID)
            elif menuSelection == "Create Rule":
                rule = self.interface.createRule()
                self.db.saveRule(rule)
            elif menuSelection == "Delete Rule":
                ruleID = self.interface.selectID(ruleIDs)
                self.db.deleteRule(ruleID)
            elif menuSelection == "Export Rules":
                rules = self.db.exportRules()
                self.interface.exportRules(rules)
            elif menuSelection == "Import Rules":
                self.interface.importRules(self.db)

    def manageRuleGroups(self, ruleID):
        """
        Displays rule groups, with option to create, edit, delete.
        """

        ruleGroupLoop = True

        while ruleGroupLoop:
            # Display rule groups and elements
            ruleGroups = self.db.loadRuleGroups(ruleID)
            ruleGroupIDs = self.db.loadRuleGroupIDs(ruleID)
            elementIDs = self.db.loadElementIDs(ruleID)

            self.interface.displayRuleGroups(ruleGroups)

            # Display rule groups menu
            ruleGroupMenu = [
                "Create Group",
                "Edit Group",
                "Delete Group",
                "Add Element to Group",
                "Edit Element",
                "Delete Element",
                "Back"
            ]
            menuSelection = self.interface.menuSelection(ruleGroupMenu)

            if menuSelection == "Back":
                ruleGroupLoop = False
            elif menuSelection == "Create Group":
                ruleGroup = self.interface.createRuleGroup(ruleID)
                self.db.saveRuleGroup(ruleGroup)
            elif menuSelection == "Edit Group":
                groupID = self.interface.selectID(ruleGroupIDs)
                ruleGroup = self.interface.createRuleGroup(ruleID)
                self.db.editRuleGroup(groupID, ruleGroup)
            elif menuSelection == "Delete Group":
                groupID = self.interface.selectID(ruleGroupIDs)
                self.db.deleteRuleGroup(groupID)
            elif menuSelection == "Add Element to Group":
                groupID = self.interface.selectID(ruleGroupIDs)
                ruleTypes = self.db.getRuleTypes()
                groupElement = self.interface.createGroupElement(
                    groupID,
                    ruleTypes
                )
                self.db.createGroupElement(groupElement)
            elif menuSelection == "Edit Element":
                elementID = self.interface.selectID(elementIDs)
                ruleTypes = self.db.getRuleTypes()
                groupElement = self.interface.createGroupElement(
                    None,
                    ruleTypes
                )
                self.db.editGroupElement(elementID, groupElement)
            elif menuSelection == "Delete Element":
                elementID = self.interface.selectID(elementIDs)
                self.db.deleteGroupElement(elementID)

    def evaluateRules(self, date, d, r):
        """
        Evaluate rules to see if the user should drive or bike.

        date = a date in mm/dd/yyyy format
        d = departure time (0-24)
        r = return time (0-24)
        """

        rules = self.db.getRules()
        score = 0
        relevantRules = []

        for i in rules:

            if i['tripTime'] == 'Return':
                time = r
            else:
                time = d

            rResult = True

            for g in i['groups']:
                if g['operator'] == "AND":
                    gResult = True
                    for e in g['elements']:
                        eResult = self.evaluateElement(
                            date=date,
                            time=time,
                            element=e
                        )

                        if eResult is False:
                            gResult = False
                            break
                elif g['operator'] == "OR":
                    gResult = False
                    for e in g['elements']:
                        eResult = self.evaluateElement(
                            date=date,
                            time=time,
                            element=e
                        )

                        if eResult is True:
                            gResult = True
                            break

                if gResult is False:
                    rResult = False
                    break

            if rResult is True:
                score += i['weight']
                relevantRules.append(i)

        return {
            "score": score,
            "bike": score < 10,
            "relevantRules": relevantRules
        }

    def evaluateElement(self, date, time, element):
        """
        Evaluates a rule element.

        date = date in mm/dd/yyyy format
        time = time (hour only) in 0-24 format
        element = element object containing
        name (name of the weather metric), operator, and value
        """

        forecastValue = self.weather.getForecastValue(
            weatherElement=element['weatherElement'],
            date=date,
            time=time
        )

        # Take this out later?
        result = "None"

        if element['operator'] == ">=":
            result = forecastValue >= int(element['value'])
        elif element['operator'] == "CONTAINS":
            result = element['value'] in forecastValue
        elif element['operator'] == "NOT CONTAINS":
            result = element['value'] not in forecastValue
        elif element['operator'] == "=":
            result = str(forecastValue) == str(element['value'])
        elif element['operator'] == "<=":
            result = forecastValue <= int(element['value'])
        elif element['operator'] == "<":
            result = forecastValue < int(element['value'])
        elif element['operator'] == ">":
            result = forecastValue > int(element['value'])

        print(
            forecastValue,
            element['operator'],
            element['value'],
            ":",
            result
        )

        return result


if __name__ == '__main__':
    # Run the program
    s = Should_I_Bike()
    s.runProgram()
