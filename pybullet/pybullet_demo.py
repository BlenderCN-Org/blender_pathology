import pybullet as p
import time

print( p.getAPIVersion() )

p.connect( p.GUI )

floorPosition = [ 0, 0, -10 ]
floorOrientation = p.getQuaternionFromEuler( [ 0, 0, 0 ] )
floorSize = [ 10, 10, 10 ]

part0Position = [ 0, 0, 10 ]
part0Orientation = p.getQuaternionFromEuler( [ 1.45, 2.56, 1.8 ] )
part0Size = [ 1, 1, 1 ]

part1Position = [ 0, 0, 20 ]
part1Orientation = p.getQuaternionFromEuler( [ 1.45, 2.56, 1.8 ] )
part1Size = [ 1, 1, 1 ]

duckPosition = [ 3, 3, 10 ]
duckOrientation = p.getQuaternionFromEuler( [ 0, 0, 0 ] )
duckSize = [ 10, 10, 10 ]

floorColID = p.createCollisionShape( shapeType=p.GEOM_MESH, fileName="floor.obj", meshScale=floorSize )
part0ColID = p.createCollisionShape( shapeType=p.GEOM_MESH, fileName="part_0.obj", meshScale=part0Size )
part1ColID = p.createCollisionShape( shapeType=p.GEOM_MESH, fileName="part_1.obj", meshScale=part1Size )
duckColID = p.createCollisionShape( shapeType=p.GEOM_MESH, fileName="duck.obj", meshScale=duckSize )

part0MBID = p.createMultiBody( baseMass=1.0, baseCollisionShapeIndex=part0ColID, basePosition=part0Position, baseOrientation=part0Orientation )
part1MBID = p.createMultiBody( baseMass=1.0, baseCollisionShapeIndex=part1ColID, basePosition=part1Position, baseOrientation=part1Orientation )
floorMBID = p.createMultiBody( baseMass=0.0, baseCollisionShapeIndex=floorColID, basePosition=floorPosition, baseOrientation=floorOrientation )
duckMBID = p.createMultiBody( baseMass=1.0, baseCollisionShapeIndex=duckColID, basePosition=duckPosition, baseOrientation=duckOrientation )

p.setGravity( 0, 0, -9.81 )
p.setRealTimeSimulation( 1 )

while (1):
	keys = p.getKeyboardEvents()
	#print(keys)
	time.sleep( 0.01 )
	