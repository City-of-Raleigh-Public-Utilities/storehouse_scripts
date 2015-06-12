#Create Project Tracking Layer from IRIS

import arcpy
import os, sys
from datetime import datetime

arcpy.env.overwriteOutput = True

date = datetime.now().strftime("%y%m%d")
currnet = datetime.now().strftime("%y-%m-%d 00:00:00")
print date

#Converts Parcel Pin numbers to State Plane Coordinates
def pinToCoord (pin):
	if pin.isdigit():
		#Covert pin to string
		pin = str(pin)
		#Set up x and y valiables
		x = '2'
		y = ''
		#Loop through the index sorting by even on odd
		for index, value in enumerate(pin):
			if index % 2 == 0:
				x+=value
			else:
				y+=value
		#Add Zeros to ends
		x+='0'
		y+='0'
		#Add x and y variables to dictionary and convert to ints
		coordinates = {'x': int(x), 'y': int(y)}
		Ax = coordinates['x'] - 100
		Ay = coordinates['y'] + 100
		Bx = coordinates['x'] + 100
		By = coordinates['y'] + 100
		Cx = coordinates['x'] + 100
		Cy = coordinates['y'] - 100
		Dx = coordinates['x'] - 100
		Dy = coordinates['y'] - 100
		polygon = [[Ax,Ay],[Bx, By], [Cx, Cy], [Dx, Dy]]
		array = arcpy.Array([arcpy.Point(*coords) for coords in polygon])
		finished = arcpy.Polygon(array)
	 	print polygon
		return finished

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

#Delete Temp Features
arcpy.DeleteFeatures_management('Project_Tracking_1_test')
#Get date last run
fileList = arcpy.ListFeatureClasses("parcels_*")
print fileList
listLength = len(fileList) - 1
print listLength
unDate = fileList[listLength].split('_')[1]
year = '20%s' % unDate[:-4]
date = "%s-%s-%s 00:00:00" % (year, unDate[2:4], unDate[-2:])
print date

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
# arcpy.MakeTableView_management("DEVELOPMENT_PLANS", "devPlans")
arcpy.MakeTableView_management("DEVELOPMENT_PLANS", "devPlans", "DEVPLAN_PLAN_APPROVAL_DATE >= date '{0}'".format(date))
print 'Table Views Created...'

#Inner Join Devplans_Case_History to Devplopment_Plans on DEVPLAN_ID
inner_join = arcpy.AddJoin_management("devPlanCaseHistory", "DEVPLAN_ID", "devPlans", "DEVPLAN_ID", "KEEP_COMMON")
count = int(arcpy.GetCount_management(inner_join).getOutput(0))
print "Inner join completed %d records found" % count

#Create Table of Joined Values
arcpy.CopyRows_management(inner_join, 'ApprovedDevPlans')
print 'ApprovedDevPlans table created...'

# arcpy.AddIndex_management ("ApprovedDevPlans", "DEVPLANS_CASE_HISTORY_NCPIN;", "NCPIN_INDEX")
# print 'index added to ApprovedDevPlans'

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
arcpy.FeatureClassToGeodatabase_conversion('WAKE.PROPERTY_A_RECORDED', projectTracking)
print 'Wake property copied to IRIS.gdb'

#Switch workspace to IRIS.gdb
arcpy.env.workspace = projectTracking
print 'Workspace Set to %s' % arcpy.env.workspace

#Rename WAKE.PROPERTY

arcpy.Rename_management("PROPERTY_A_RECORDED", new_name)
print "PROPERTY renamed %s" % new_name

#Add index to parcels
arcpy.AddIndex_management (new_name, "PIN_NUM;", "PIN_INDEX")
print 'index added to %s' % new_name


#Inner join IRIS data to parcel data
arcpy.MakeFeatureLayer_management (new_name, "parcels")
print 'Pacels feature layer created'
tempProjects = arcpy.AddJoin_management("parcels", "PIN_NUM", "adp", "DEVPLANS_CASE_HISTORY_NCPIN", "KEEP_COMMON")
print 'Inner join complete...'

#Create Table of Joined Values
# arcpy.CopyRows_management(inner_join, 'matchedPINs')
# arcpy.CopyFeatures_management(tempProjects, os.path.join(projectTracking, 'matchedPINs'))
# print 'ApprovedDevPlans feature class created...'
# arcpy.MakeFeatureLayer_management (os.path.join(projectTracking, 'matchedPINs'), 'tempProjects')

#Fields in the Project Tracking feature class to be updated
insertfields = ['PROJECTID', 'DEVPLANID', 'PROJECTNAME', 'CPLINK', 'NCPIN', 'DEVPLAN_APPROVAL', 'SHAPE@']


#Function to get starting projectid for project tracking layer
def getStartId (feature, field):
	count = int(arcpy.GetCount_management(feature).getOutput(0))
	print 'Project Tracking Currently has %d features' % count
	if count == 0:
		print 'Starting ProjectID: 100000'
		return 100000
	else:
		rows = arcpy.SearchCursor(feature, "1=1", "", "PROJECTID", "PROJECTID D")
		row = rows.next()
		maxId = row.getValue("PROJECTID")
		print 'Max ProjectID %d' % maxId
		return maxId

#Adds the matched parcels to the project tracking feature class
def insertParcelsWithMatchedPins (feature):
	#Get field names from join
	fieldnames = ['%s.PIN_NUM' % new_name,'ApprovedDevPlans.DEVELOPMENT_PLANS_DEVPLAN_PLANNING_LETTER_ID','ApprovedDevPlans.DEVELOPMENT_PLANS_DEVPLAN_PLANNING_NUM', 'ApprovedDevPlans.DEVELOPMENT_PLANS_DEVPLAN_PLANNING_YEAR', 'ApprovedDevPlans.DEVELOPMENT_PLANS_DEVPLAN_DEVPLAN_NAME', 'ApprovedDevPlans.DEVELOPMENT_PLANS_DEVPLAN_PLAN_APPROVAL_DATE', 'SHAPE@']
	#Switch workspace to RPUD
	arcpy.env.workspace = projectTracking
	print 'Workspace Set to %s' % arcpy.env.workspace

	#Get starting value for ProjectID count
	startID = getStartId(feature, 'PROJECTID')
	edit = arcpy.da.Editor(arcpy.env.workspace)
	edit.startEditing(False, True)
	edit.startOperation()
	print 'Editor Started...'
	#Create search cursor on join table
	with arcpy.da.InsertCursor(feature, insertfields) as insert_cursor:
		#Create insert cursor for Project Tracking Feature Class
		with arcpy.da.SearchCursor(tempProjects, fieldnames) as search_cursor:
			for search_row in search_cursor:
				startID+=1
				devPlan = '%s-%d-%d' % (search_row[1], int(search_row[2]), int(search_row[3]))
				insert_row = (startID, devPlan, search_row[4], 'http://gis.raleighnc.gov/publicutility/devplans/%s' % devPlan, search_row[0], search_row[5], search_row[6])
				result = insert_cursor.insertRow(insert_row)
				print result

	print 'Data Updated'
	edit.stopOperation()
	edit.stopEditing(True)
	print 'Edits Saved'

#Adds the unmatched parcel PIN numbers by deconstructing the PINS into coordinates
def insertFeaturesByUnmatchedPIN (featrue):
	#Create featuers layer of Project_Tracking Layer
	arcpy.MakeFeatureLayer_management (featrue, "projects")

	#Set Workspace to IRIS.gdb
	arcpy.env.workspace = projectTracking

	#Add index to ApprovedDevPlans
	arcpy.AddIndex_management ('ApprovedDevPlans', "DEVPLANS_CASE_HISTORY_NCPIN;", "NCPIN_INDEX")
	print 'index added to ApprovedDevPlans'

	#Create table view for ApprovedDevPlans
	arcpy.MakeTableView_management("ApprovedDevPlans", "AppDevPlans")

	#Join Tables
	unmatched = arcpy.AddJoin_management("AppDevPlans", "DEVPLANS_CASE_HISTORY_NCPIN", "projects", "NCPIN")

	#Select features with no PROJECTID
	selection = arcpy.SelectLayerByAttribute_management(unmatched, "NEW_SELECTION", "%s.PROJECTID IS NULL" % featrue)

	#Switch workspace to RPUD
	# arcpy.env.workspace = RPUD
	# print 'Workspace Set to %s' % arcpy.env.workspace

	#Get starting value for ProjectID count
	startID = getStartId(featrue, 'PROJECTID')


	fieldnames = ['ApprovedDevPlans.DEVPLANS_CASE_HISTORY_NCPIN','ApprovedDevPlans.DEVELOPMENT_PLANS_DEVPLAN_PLANNING_LETTER_ID','ApprovedDevPlans.DEVELOPMENT_PLANS_DEVPLAN_PLANNING_NUM', 'ApprovedDevPlans.DEVELOPMENT_PLANS_DEVPLAN_PLANNING_YEAR', 'ApprovedDevPlans.DEVELOPMENT_PLANS_DEVPLAN_DEVPLAN_NAME', 'ApprovedDevPlans.DEVELOPMENT_PLANS_DEVPLAN_PLAN_APPROVAL_DATE']
	edit = arcpy.da.Editor(arcpy.env.workspace)
	edit.startEditing(False, True)
	edit.startOperation()
	print 'Editor Started...'
	#Create search cursor on join table
	with arcpy.da.SearchCursor(selection, fieldnames) as search_cursor:
		#Create insert cursor for Project Tracking Feature Class
		with arcpy.da.InsertCursor(featrue, insertfields) as insert_cursor:
			for search_row in search_cursor:
				if type(search_row[0]) is unicode:
					if search_row[0].isdigit():
						shape = pinToCoord(search_row[0])
						startID+=1
						devPlan = '%s-%d-%d' % (search_row[1], int(search_row[2]), int(search_row[3]))
						insert_row = (startID, devPlan, search_row[4], 'http://gis.raleighnc.gov/publicutility/devplans/%s' % devPlan, search_row[0], search_row[5], shape)
						result = insert_cursor.insertRow(insert_row)
						print result


	print 'Data Updated'
	edit.stopOperation()
	edit.stopEditing(True)
	print 'Edits Saved'





#Disolve new data and add to ProjectTracking Feature Class
def dissolveFeatureClass(fc):
	tempDissovle = os.path.join(projectTracking, 'dissolve')
	dissolve_fields = ['DEVPLANID', 'PROJECTNAME', 'FORMERNAME', 'ALIAS', 'CIP', 'WATER', 'SEWER', 'REUSE', 'STORM', 'WATERUPDATEDBY', 'WATERUPDATEDWHEN', 'SEWERUPDATEDBY', 'SEWERUPDATEDWHEN', 'REUSEUPDATEDBY', 'REUSEUPDATEDWHEN', 'CPLINK', 'ABLINK', 'ACCEPTANCEDATE', 'WARRANTYENDDATE', 'NOTES', 'TAGS', 'DEVPLAN_APPROVAL']
	stat_fields = [['PROJECTID', 'MAX'],['NCPIN', 'COUNT']]
	print 'Starting Dissolve...'
	arcpy.Dissolve_management(fc, tempDissovle, dissolve_fields, stat_fields)
	print 'Dissolve complete'


def getUniqueValues(fc, field):
	allProjects = []
	with arcpy.da.SearchCursor(fc, field) as checkcursor:
		for value in checkcursor:
			allProjects.append(value)
	uniqueProject = set(allProjects)
	return uniqueProject

def insertDissolvedFeatures (finalfc):
	#Switch workspace to RPUD
	arcpy.env.workspace = RPUD
	print 'Workspace Set to %s' % arcpy.env.workspace
	#Fields in the Project Tracking feature class to be updated
	updatefields = ['PROJECTNAME', 'FORMERNAME', 'SHAPE@']
	finalfields = ['PROJECTID', 'DEVPLANID', 'PROJECTNAME', 'CPLINK', 'DEVPLAN_APPROVAL', 'SHAPE@']
	tempFields = ['DEVPLANID', 'PROJECTNAME', 'CPLINK', 'DEVPLAN_APPROVAL', 'MAX_PROJECTID', 'SHAPE@']

	tempDissovle = os.path.join(projectTracking, 'dissolve')

	values = getUniqueValues(finalfc, 'DEVPLANID')

	edit = arcpy.da.Editor(arcpy.env.workspace)
	edit.startEditing(False, True)
	edit.startOperation()
	print 'Editor Started...'

	with arcpy.da.SearchCursor(tempDissovle, tempFields) as scursor:
		with arcpy.da.InsertCursor(finalfc, finalfields) as icursor:
			for info in scursor:
				if info[0] in values:
					wc = 'DEVPLANID = %s' % info[0]
					with arcpy.da.UpdateCursor(finalfc, updatefields, wc) as ucursor:
						for row in ucursor:
							row[2] = info[5] #Shape
							if info[1] != row[0]:
								row[1] = row[0]
								row[0] = info[1]

							result = ucursor.updateRow(row)
							print 'Update: {0}'.format(result)
				else:
					shape = info[5]
					startID = info[4]
					devPlan = info[0]
					insert_row = (startID, devPlan, info[1], 'http://gis.raleighnc.gov/publicutility/devplans/%s' % devPlan, info[3], shape)
					result = icursor.insertRow(insert_row)
					print 'Insert: {0}'.format(result)

	print 'Data Updated'
	edit.stopOperation()
	edit.stopEditing(True)
	print 'Edits Saved'


def main(fc):
	insertParcelsWithMatchedPins(fc)
	insertFeaturesByUnmatchedPIN(fc)
	dissolveFeatureClass(fc)
	insertDissolvedFeatures('RPUD.Project_Tracking')

main('Project_Tracking_1_test')
