import sqlite3

"""
Handles all the database stuff
"""


class DB():

    def __init__(self, should_i_bike):
        """
        Connect to Database and initialize variables
        """

        self.dbPath = "should-i-bike/should-i-bike.db"
        self.con = sqlite3.connect(self.dbPath)
        self.cur = self.con.cursor()
        self.build_db()

        self.should_i_bike = should_i_bike

    def build_db(self):
        """
        Creates the should-i-bike database and all its tables
        """

        # Create tables if they don't already exist (preserves data across runs)

        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS rule_types(
                name,
                weather_element
                )
            """)

        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS rules(
                name,
                description,
                rule_type_id,
                weather_element,
                operator,
                trip_time,
                target_value,
                weight
            )
        """)

        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS settings(
                name,
                value,
                description
            )
        """)

        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS rule_groups(
                rule_id,
                operator
            )
        """)

        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS rule_group_elements(
                rule_group_id,
                rule_type_id,
                operator,
                value
            )
        """)

        # Populate default rule types (only if table is empty)

        self.cur.execute("""
            INSERT OR IGNORE INTO rule_types SELECT * FROM (
                SELECT 'Temperature', 'temperature' UNION ALL
                SELECT 'Wind Speed', 'windSpeed' UNION ALL
                SELECT 'Wind Direction', 'windDirection' UNION ALL
                SELECT 'Wind Gust', 'windGust' UNION ALL
                SELECT 'Visibility', 'visibility' UNION ALL
                SELECT 'Rain Chance', 'probabilityOfPrecipitation'
            ) WHERE NOT EXISTS (SELECT 1 FROM rule_types)
        """)
        self.con.commit()

        # Populate default settings
        # self.should_i_bike.zip = '67114'
        # self.should_i_bike.country = 'US'
        # self.should_i_bike.defaultDeparture = 7
        # self.should_i_bike.defaultReturn = 17
        # self.should_i_bike.hoursReturned

        self.cur.execute("""
            INSERT INTO settings SELECT * FROM (
                SELECT 'Zip','67114','Zip code for the weather forecast' UNION ALL
                SELECT 'Country','US','I do not remember what this does. Best leave it be.' UNION ALL
                SELECT 'Default Departure',7,'Default departure time. 00-24' UNION ALL
                SELECT 'Default Return',17,'Default return time. 00-24' UNION ALL
                SELECT 'Hours Returned',48,'Number of hours to return in the hourly forecast'
            ) WHERE NOT EXISTS (SELECT 1 FROM settings)
        """)
        self.con.commit()

    def insertRuleType(self, name):
        """
        Creates a new rule type
        """

        rule_type = (name,)

        self.cur.execute("INSERT INTO rule_types VALUES ?", rule_type)
        self.con.commit()

    def loadSettings(self, type='dict'):
        """
        Loads settings from the settings table.
        """

        rows = self.cur.execute("""
            SELECT rowid, name, value, description from settings
        """)

        if type == 'dict':
            settings = {}

            for row in rows.fetchall():
                settings[row[1]] = {
                    "value": row[2],
                    "description": row[3],
                    "rowid": row[0]
                }
        elif type == 'array':
            settings = []

            for row in rows.fetchall():
                settings.append(row)

        return settings

    def updateSetting(self, settingName, value):
        """
        Changes a setting by the name
        """

        self.cur.execute(
            "UPDATE settings SET value = ? WHERE name = ?",
            (value, settingName)
        )
        self.con.commit()

    def loadRules(self):
        """
        Loads all rules
        """

        rows = self.cur.execute("""
            SELECT
            rowid,
            name,
            trip_time,
            weight
            FROM rules
            ORDER BY name
        """)

        rules = []
        for row in rows.fetchall():
            rules.append(row)

        return rules

    def loadRuleGroups(self, ruleID):
        """ Loads rule groups for specified rule. """

        rows = self.cur.execute(
            """
            SELECT
            rowid,
            operator
            FROM rule_groups
            WHERE rule_id = ?
            """,
            (ruleID,)
        )

        ruleGroups = []
        for r in rows.fetchall():
            # Get rule group elements
            rgeRows = self.cur.execute(
                """
                SELECT
                rge.rowid,
                rt.name,
                rge.operator,
                rge.value
                FROM rule_group_elements rge
                INNER JOIN rule_types rt ON rge.rule_type_id = rt.rowid
                WHERE rge.rule_group_id = ?
                """,
                (r[0],)
            )

            elements = []
            for rge in rgeRows:
                element = {
                    "id": rge[0],
                    "type": rge[1],
                    "operator": rge[2],
                    "value": rge[3]
                }
                elements.append(element)

            ruleGroups.append(
                {
                    "id": r[0],
                    "operator": r[1],
                    "elements": elements
                }
            )

        return ruleGroups

    def loadRuleGroupIDs(self, ruleID):
        """
        Returns just the ids of rule groups for a rule.
        """

        ruleGroupIDs = self.cur.execute(
            """
            SELECT rowid FROM rule_groups WHERE rule_id = ?
            """,
            (ruleID,)
        )

        ruleGroups = []

        for r in ruleGroupIDs.fetchall():
            ruleGroups.append(r[0])

        return ruleGroups

    def saveRuleGroup(self, ruleGroup):
        """
        Saves a rule group.
        ruleGroup is a dictionary that has a ruleID element and
        an operator element.
        """

        self.cur.execute(
            """
            INSERT INTO rule_groups (
            rule_id,
            operator
            )
            VALUES(?, ?)
            """,
            (ruleGroup['ruleID'], ruleGroup['operator'])
        )
        self.con.commit()
        return self.cur.lastrowid

    def editRuleGroup(self, groupID, ruleGroup):
        """
        Edits an existing rule group.
        ruleGroup is a dictionary that has a ruleID element and
        an operator elements.
        """

        self.cur.execute(
            """
            UPDATE rule_groups SET
            rule_id = ?,
            operator = ?
            WHERE rowid = ?
            """,
            (
                ruleGroup['ruleID'],
                ruleGroup['operator'],
                groupID
            )
        )
        self.con.commit()

    def deleteRuleGroup(self, groupID):
        """ Deletes a rule group. """

        self.cur.execute(
            """
            DELETE from rule_groups WHERE rowid = ?
            """,
            (groupID,)
        )
        self.cur.execute(
            """
            DELETE FROM rule_group_elements
            WHERE rule_group_id = ?
            """,
            (groupID,)
        )
        self.con.commit()

    def getRuleTypes(self):
        """ Returns a list of rule types """

        rows = self.cur.execute(
            """
            SELECT name from rule_types
            """
        )

        ruleTypes = []

        for r in rows.fetchall():
            ruleTypes.append(r[0])

        return ruleTypes

    def getRuleTypeID(self, ruleType):
        """ Returns the ID for a specified rule type. """

        rows = self.cur.execute(
            """
            SELECT rowid FROM rule_types WHERE name = ?
            """,
            (ruleType,)
        )

        return rows.fetchall()[0][0]

    def createGroupElement(self, groupElement):
        """
        Saves a group element in the database.

        groupElement is a dictionary that has the following
        attributes: groupID, ruleType (this is the name of
        the type, not the ID), operator, value.
        """

        ruletypeID = self.getRuleTypeID(groupElement['ruleType'])

        self.cur.execute(
            """
            INSERT INTO rule_group_elements (
            rule_group_id,
            rule_type_id,
            operator,
            value
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                groupElement['groupID'],
                ruletypeID,
                groupElement['operator'],
                groupElement['value']
            )
        )
        self.con.commit()

    def loadElementIDs(self, ruleID):
        """
        Returns an array of element IDs for the specified rule.
        """

        rows = self.cur.execute(
            """
            SELECT rge.rowid
            FROM rule_group_elements rge
            INNER JOIN rule_groups rg on rge.rule_group_id = rg.rowid
            WHERE rg.rule_id = ?
            """,
            (ruleID,)
        )

        elementIDs = []

        for r in rows.fetchall():
            elementIDs.append(r[0])

        return elementIDs

    def editGroupElement(self, elementID, groupElement):
        """
        Edits an existing rule group element.

        groupElement is a dictionary with the following values:
        groupID (not used in this case), ruleType (this it the name
        of the type, not the ID), operator, value.
        """

        ruleTypeID = self.getRuleTypeID(groupElement['ruleType'])

        self.cur.execute(
            """
            UPDATE rule_group_elements SET
            rule_type_id = ?,
            operator = ?,
            value = ?
            WHERE rowid = ?
            """,
            (
                ruleTypeID,
                groupElement['operator'],
                groupElement['value'],
                elementID
            )
        )
        self.con.commit()

    def deleteGroupElement(self, elementID):
        """ Deletes a specified rule group element """

        self.cur.execute(
            """
            DELETE FROM rule_group_elements
            WHERE rowid = ?
            """,
            (elementID,)
        )

    def saveRule(self, rule):
        """ Saves a new rule in the DB. """

        self.cur.execute(
            """
            INSERT INTO rules(
            name,
            trip_time,
            weight
            )
            VALUES(?, ?, ?)
            """,
            (
                rule['name'],
                rule['tripTime'],
                rule['weight']
            )
        )
        self.con.commit()
        return self.cur.lastrowid

    def deleteRule(self, ruleID):
        """ Deletes a rule. """

        # Get all associated rule groupings so that elements can be deleted
        rows = self.cur.execute(
            """
            SELECT rowid FROM rule_groups WHERE rule_id = ?
            """,
            (ruleID,)
        )

        # Delete the rule groups and elements
        for r in rows.fetchall():
            self.deleteRuleGroup(r[0])

        # Delete the rule
        self.cur.execute(
            """
            DELETE FROM rules WHERE rowid = ?
            """,
            (ruleID,)
        )
        self.con.commit()

    def editRule(self, ruleID, rule):
        """
        Edits an existing rule.

        rule is a dictionary containing name, tripTime and weight elements.
        """

        self.cur.execute(
            """
            UPDATE rules SET
            name = ?,
            trip_time = ?,
            weight = ?
            WHERE rowid = ?
            """,
            (
                rule['name'],
                rule['tripTime'],
                rule['weight'],
                ruleID,
            )
        )
        self.con.commit()

    def getRules(self):
        """ Returns all the rules with groupings and elements. """

        rules = []

        ruleQuery = self.cur.execute(
            """
            SELECT rowid, name, trip_time, weight
            FROM rules
            """
        )

        for r in ruleQuery.fetchall():

            # Get groups
            groups = []
            groupQuery = self.cur.execute(
                """
                SELECT rowid, operator
                FROM rule_groups
                WHERE rule_id = ?
                """,
                (r[0],)
            )

            for g in groupQuery.fetchall():

                # Get elements
                elements = []
                elementQuery = self.cur.execute(
                    """
                    SELECT rt.name, rge.operator, rge.value, rt.weather_element
                    FROM rule_group_elements rge
                    INNER JOIN rule_types rt
                    ON rge.rule_type_id = rt.rowid
                    WHERE rge.rule_group_id = ?
                    """,
                    (g[0],)
                )

                for e in elementQuery.fetchall():
                    elements.append({
                        "name": e[0],
                        "operator": e[1],
                        "value": e[2],
                        "weatherElement": e[3]
                    })

                groups.append({
                    "operator": g[1],
                    "elements": elements
                })

            rules.append({
                "name": r[1],
                "tripTime": r[2],
                "weight": r[3],
                "groups": groups
            })

        return rules

    def exportRules(self):
        """ Returns all rules serialized to the portable export format. """
        raw = self.getRules()
        export = []
        for r in raw:
            groups = []
            for g in r['groups']:
                elements = []
                for e in g['elements']:
                    elements.append({
                        'rule_type': e['name'],
                        'operator':  e['operator'],
                        'value':     e['value']
                    })
                groups.append({'operator': g['operator'], 'elements': elements})
            export.append({
                'name':      r['name'],
                'trip_time': r['tripTime'],
                'weight':    r['weight'],
                'groups':    groups
            })
        return export

    def importRules(self, rules):
        """
        Imports rules from the portable export format. Adds to existing rules.
        Returns {'imported': int, 'skipped_elements': [str]}.
        """
        valid_types = set(self.getRuleTypes())
        imported = 0
        skipped_elements = []

        for rule_data in rules:
            rule_id = self.saveRule({
                'name':     rule_data['name'],
                'tripTime': rule_data['trip_time'],
                'weight':   int(rule_data['weight'])
            })

            for group_data in rule_data.get('groups', []):
                group_id = self.saveRuleGroup({
                    'ruleID':   rule_id,
                    'operator': group_data['operator']
                })

                for elem_data in group_data.get('elements', []):
                    rt_name = elem_data['rule_type']
                    if rt_name not in valid_types:
                        skipped_elements.append(
                            f"Rule '{rule_data['name']}': unknown rule_type '{rt_name}' skipped"
                        )
                        continue
                    self.createGroupElement({
                        'groupID':  group_id,
                        'ruleType': rt_name,
                        'operator': elem_data['operator'],
                        'value':    str(elem_data['value'])
                    })

            imported += 1

        return {'imported': imported, 'skipped_elements': skipped_elements}
