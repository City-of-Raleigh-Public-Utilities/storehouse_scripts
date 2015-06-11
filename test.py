#Create Project Tracking Layer from IRIS

import arcpy
import os, sys
from datetime import datetime

arcpy.env.overwriteOutput = True

date = datetime.now().strftime("%y%m%d")
currnet = datetime.now().strftime("%y-%m-%d 00:00:00")
print date

#Name of new Property feature class
new_name = 'parcels_{0}'.format(date)

#Set database connection variable
RPUD = os.path.join(os.path.dirname(sys.argv[0]), 'RPUD.sde')
WAKE = os.path.join(os.path.dirname(sys.argv[0]), 'WAKE.sde')
projectTracking = os.path.join(os.path.dirname(sys.argv[0]), 'IRIS.gdb')
IRISPRD = os.path.join(os.path.dirname(sys.argv[0]), 'IRISPRD.sde')

#Set workspace to IRISPRD
arcpy.env.workspace = projectTracking
print 'Workspace Set to %s' % arcpy.env.workspace

#Check for existing tables and delete
tables = ["DEVPLANS_CASE_HISTORY", "DEVELOPMENT_PLANS", "PROPERTY", new_name, 'ApprovedDevPlans']
for table in tables:
	if arcpy.Exists(table):
		arcpy.Delete_management(table)

#Set workspace to IRISPRD
arcpy.env.workspace = IRISPRD
print 'Workspace Set to %s' % arcpy.env.workspace

#Copy tables from IRISPRD to IRIS.gdb
arcpy.TableToGeodatabase_conversion(["IRIS.DEVPLANS_CASE_HISTORY", "IRIS.DEVELOPMENT_PLANS"], projectTracking)
print 'Tables from IRIS copied to IRIS.gdb'

#Switch workspace to IRIS.gdb
arcpy.env.workspace = projectTracking
print 'Workspace Set to %s' % arcpy.env.workspace

#Create table views for IRIS data
arcpy.MakeTableView_management("DEVPLANS_CASE_HISTORY", "devPlanCaseHistory")
arcpy.MakeTableView_management("DEVELOPMENT_PLANS", "devPlans", "DEVPLAN_PLAN_APPROVAL_DATE >= date '2009-01-01 00:00:00'")
print 'Table Views Created...'

#Inner Join Devplans_Case_History to Devplopment_Plans on DEVPLAN_ID
inner_join = arcpy.AddJoin_management("devPlanCaseHistory", "DEVPLAN_ID", "devPlans", "DEVPLAN_ID", "KEEP_COMMON")
count = int(arcpy.GetCount_management(inner_join).getOutput(0))
print "Inner join completed %d records found" % count

#Create Table of Joined Values
arcpy.CopyRows_management(inner_join, 'ApprovedDevPlans')
print 'ApprovedDevPlans table created...'
arcpy.MakeTableView_management("ApprovedDevPlans", "adp")
#Exit function if join produces Zero results
def endIfZero (count):
	if count == 0:
		print 'Script Completed...\n\tNo new records found.'
		sys.exit()


endIfZero(count)

#Switch workspace to WAKE
arcpy.env.workspace = WAKE
print 'Workspace Set to %s' % arcpy.env.workspace

#Copy parcles to local geodatabase
arcpy.FeatureClassToGeodatabase_conversion('WAKE.PROPERTY', projectTracking)
print 'Wake property copied to IRIS.gdb'

#Switch workspace to IRIS.gdb
arcpy.env.workspace = projectTracking
print 'Workspace Set to %s' % arcpy.env.workspace

#Rename WAKE.PROPERTY

arcpy.Rename_management("PROPERTY", new_name)
print "PROPERTY renamed %s" % new_name

#Add index to parcels
arcpy.AddIndex_management (new_name, "PIN_NUM;", "PIN_INDEX")
print 'index added to %s' % new_name

#Inner join IRIS data to parcel data
arcpy.MakeFeatureLayer_management (new_name, "parcels")
print 'Pacels feature layer created'
# tempProjects = arcpy.AddJoin_management("parcels", "PIN_NUM", "adp", "DEVPLANS_CASE_HISTORY_NCPIN", "KEEP_COMMON")
# print 'Inner join complete...'

#Get field names from join
fieldnames = ['%s.PIN_NUM' % new_name,'ApprovedDevPlans.DEVELOPMENT_PLANS_DEVPLAN_PLANNING_LETTER_ID','ApprovedDevPlans.DEVELOPMENT_PLANS_DEVPLAN_PLANNING_NUM', 'ApprovedDevPlans.DEVELOPMENT_PLANS_DEVPLAN_PLANNING_YEAR', 'ApprovedDevPlans.DEVELOPMENT_PLANS_DEVPLAN_DEVPLAN_NAME', 'ApprovedDevPlans.DEVELOPMENT_PLANS_DEVPLAN_PLAN_APPROVAL_DATE', 'SHAPE@']
insertfields = ['PROJECTID', 'DEVPLANID', 'PROJECTNAME', 'CPLINK', 'NCPIN', 'DEVPLAN_APPROVEAL', 'SHAPE@']

#Function to get starting projectid for project tracking layer
def getStartId (feature, field):
	count = int(arcpy.GetCount_management(feature).getOutput(0))
	if count == 0:
		print 'Starting ProjectID: 100000'
		return 100000
	else: 
		with arcpy.da.SearchCursor(feature, field, sql_clause=(None, 'ORDER BY %s ASC' % field)) as cursor:
			for row in cursor:
				start = row[0]
			print 'Starting ProjectID: %d' % start
			return start

#Switch workspace to RPUD
arcpy.env.workspace = RPUD
print 'Workspace Set to %s' % arcpy.env.workspace

#Get starting value for ProjectID count
startID = getStartId('RPUD.ProjectTracking', 'PROJECTID')

ptrack = os.path.join(projectTracking, "ProjectTracking_4")
#Start Edit Session
edit = arcpy.da.Editor(projectTracking)
edit.startEditing(False, True)                      
edit.startOperation()
#Create search cursor on join table
# with arcpy.da.SearchCursor(tempProjects, fieldnames) as search_cursor:
# 	#Create insert cursor for Project Tracking Feature Class
# 	with arcpy.da.InsertCursor(ptrack, insertfields) as insert_cursor:
# 		for search_row in search_cursor:
# 			startID+=1
# 			devPlan = '%s-%d-%d' % (search_row[1], int(search_row[2]), int(search_row[3]))
# 			insert_row = (startID, devPlan, search_row[4], 'http://gis.raleighnc.gov/publicutility/devplans/%s' % devPlan, search_row[0], search_row[5], search_row[6])
# 			result = insert_cursor.insertRow(insert_row)
# 			print result

# print 'Data Updated'
# #Stop Editing
# edit.stopOperation()
# edit.stopEditing(True)
# print 'Edits Saved'

# ptrack = os.path.join(projectTracking, "ProjectTracking_1")

parcelfields= ['PIN_NUM', 'SHAPE@']
fieldnames = ['DEVPLANS_CASE_HISTORY_NCPIN','DEVELOPMENT_PLANS_DEVPLAN_PLANNING_LETTER_ID','DEVELOPMENT_PLANS_DEVPLAN_PLANNING_NUM', 'DEVELOPMENT_PLANS_DEVPLAN_PLANNING_YEAR', 'DEVELOPMENT_PLANS_DEVPLAN_DEVPLAN_NAME', 'DEVELOPMENT_PLANS_DEVPLAN_PLAN_APPROVAL_DATE']
# with arcpy.da.Editor(arcpy.env.workspace) as edit:
with arcpy.da.InsertCursor(ptrack, insertfields) as insert_cursor:
	with arcpy.da.SearchCursor("adp", fieldnames) as search_cursor:
		fn = [f.name for f in arcpy.ListFields("adp")]
		print fn
		for search_row in search_cursor:
			where = "PIN_NUM = '%d'" % int(search_row[0])
			arcpy.SelectLayerByAttribute_management("parcels", "CLEAR_SELECTION")
			arcpy.SelectLayerByAttribute_management("parcels", "NEW_SELECTION", where)
			with arcpy.da.SearchCursor("parcels", parcelfields) as parcel_cursor:
				for prow in parcel_cursor:
					startID+=1
					devPlan = '%s-%d-%d' % (search_row[1], int(search_row[2]), int(search_row[3]))
					insert_row = (startID, devPlan, search_row[4], 'http://gis.raleighnc.gov/publicutility/devplans/%s' % devPlan, search_row[0], search_row[5], prow[1])
					print insert_row
					result = insert_cursor.insertRow(insert_row)
					print result

#Stop Editing
edit.stopOperation()
edit.stopEditing(True)








