import arcpy, os, sys

RPUD = os.path.join(os.path.dirname(sys.argv[0]), 'RPUD.sde')

arcpy.env.workspace = RPUD
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

def updateId (feature):
  maxId = getStartId('RPUD.Project_Tracking', 'PROJECTID')
  count = 0
  cursor = arcpy.UpdateCursor(feature, 'PROJECTID IS NULL', fields='PROJECTID')
  for row in cursor:
    #Inc ProjectId
    maxId+=1
    count+=1

    row.setValue('PROJECTID', maxId)
    cursor.updateRow(row)

  del row
  del cursor

  print '%d projects added' % count
  print maxId

updateId('RPUD.Project_Tracking')
