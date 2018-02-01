
import os
import sys, getopt
import math
from random import *

import bpy
from bpy.props import *
import mathutils
from mathutils import Vector, Matrix

import argparse
import errno    

def simulate( infile='', parts=1, outdir='./outdir', runs='10', frames='250', movie=False, verbose=False, blendfile=False ):

    # helper function to emulate mkdir -p
    def mkdir_p( path ):
        try:
            os.makedirs(path)
        except OSError as exc:  # Python >2.5
            if exc.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else:
                raise

    # calculate the union of bounding boxes in world coords
    def calculate_world_bounds( objs ):

        # minX. maxX, minY, maxY, minZ, maxZ
        bounds = [ math.inf, -math.inf, math.inf, -math.inf, math.inf, -math.inf ]

        if type( objs ) != list:
            objs = [ objs ]

        for obj in objs:
            corners = [ obj.matrix_world * Vector( corner ) for corner in obj.bound_box ]
            for p in corners:
                for d in range( 0, 3 ):
                    if( p[ d ] < bounds[ d * 2 + 0 ] ):
                        bounds[ d * 2 + 0 ] = p[ d ]
                    if( p[ d ] > bounds[ d * 2 + 1 ] ):
                        bounds[ d * 2 + 1 ] = p[ d ]

        return bounds

    # create a new mesh object, we use the 'data' method, and add
    # the resulting object to the scene by hand. the other option would be to 
    # use the creation operator, see: https://wiki.blender.org/index.php/Dev:Py/Scripts/Cookbook/Code_snippets/Three_ways_to_create_objects
    def add_trimesh( name, trimesh ):
        center = trimesh.center_mass
        vertices = []
        faces = []
        for v in trimesh.vertices:
            vertices.append( Vector( ( v[ 0 ] - center[ 0 ], v[ 1 ] - center[ 1 ], v[ 2 ] - center[ 2 ] ) ) )
        for f in trimesh.faces:
            faces.append( [ f[ 0 ], f[ 1 ], f[ 2 ] ] )
        nm = bpy.data.meshes.new( name + '_mesh' )
        nm.from_pydata( vertices, [], faces )
        obj = bpy.data.objects.new( name + '_obj', nm )
        obj.location = Vector( (center[ 0 ], center[ 1 ], center[ 2 ]) )
        bpy.context.scene.objects.link( obj )
        bpy.context.scene.update()
        return obj

    # notify blender that we select one or more objects
    def select_objects( obj ):
        bpy.ops.object.select_all( action = 'DESELECT' )
        if isinstance( obj, list ):
            for i in obj:
                i.select = True
        else:
            obj.select = True
        bpy.context.scene.update()

    # make the camera look at a given point (center) from a given point (eye), using the camera-y axis as up vector
    def set_camera_look_at( eye=Vector( ( 0, 0, 10 ) ), center=Vector( ( 0, 0, 0 ) ) ):
        bpy.context.scene.camera.location = eye.copy()
        direction = center - eye
        # point the cameras '-Z' and use its 'Y' as up
        quat = direction.to_track_quat('-Z', 'Y')
        # assume we're using euler rotation
        bpy.context.scene.camera.rotation_euler = quat.to_euler()

    # create and add a material to the scene
    def add_material( object,   name = 'default_mterial',
                                shader = 'LAMBERT',
                                diffuse = ( 0.5, 0.5, 0.5 ),
                                diffuse_intensity = 0.5,
                                specular = ( 1.0, 1.0, 1.0 ),
                                specular_intensity = 0.1,
                                alpha = 1.0,
                                ambient = 0.2):

        mat = bpy.data.materials.new( name )
        object.data.materials.append( mat )

        mat.diffuse_color = diffuse
        mat.diffuse_shader = shader
        mat.diffuse_intensity = diffuse_intensity
        mat.specular_color = specular
        mat.specular_intensity = specular_intensity
        mat.alpha = alpha
        mat.ambient = ambient
        return mat

    def add_lamp( type='SUN', location=Vector( (0,0,10) ) ):
        bpy.ops.object.lamp_add( type=type, radius=1, view_align=False, location=location, 
        layers=(True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False))
        bpy.context.object.data.shadow_soft_size = 0.01
        bpy.context.object.data.cycles.cast_shadow = True

    def set_physics_parameters( solver_iterations=10, steps_per_second=60, time_scale=1.0, use_split_impulse=False, gravity=Vector( ( 0, 0, -9.81 ) ) ):
        # add a physics context
        bpy.ops.rigidbody.world_add()
        bpy.context.scene.rigidbody_world.solver_iterations = solver_iterations
        bpy.context.scene.rigidbody_world.steps_per_second = steps_per_second
        bpy.context.scene.rigidbody_world.time_scale = time_scale
        bpy.context.scene.rigidbody_world.use_split_impulse = use_split_impulse
        bpy.context.scene.gravity = gravity

    def set_render_parameters( res_x=256, res_y=256, format='AVI_JPEG', frame_start=1, frame_end=256 ):
        bpy.context.scene.render.resolution_x = res_x
        bpy.context.scene.render.resolution_y = res_y
        bpy.context.scene.render.resolution_percentage = 100
        bpy.context.scene.render.pixel_aspect_x = 1
        bpy.context.scene.render.pixel_aspect_y = 1
        bpy.context.scene.render.use_file_extension = True
        bpy.context.scene.render.image_settings.color_mode ='RGBA'
        bpy.context.scene.render.image_settings.file_format = format 
        bpy.context.scene.render.filepath = os.getcwd()
        bpy.context.scene.render.image_settings.compression = 90
        bpy.context.scene.frame_start = frame_start
        bpy.context.scene.frame_end = frame_end
        if bpy.context.scene.rigidbody_world != None:
            bpy.context.scene.rigidbody_world.point_cache.frame_end = frame_end + 1

    def set_camera_parameters( location=Vector( (0, 0, 0) ), rotation=Vector( (0, 0, 0) ), fov=60.0, clip_start=0.1, clip_end=10000 ):
        bpy.context.scene.camera.data.angle = fov * ( math.pi / 180.0 )
        bpy.context.scene.camera.data.clip_end = clip_end
        bpy.context.scene.camera.rotation_mode = 'XYZ'
        bpy.context.scene.camera.location = location.copy()
        bpy.context.scene.camera.rotation_euler[ 0 ] = rotation.x * ( math.pi / 180.0 )
        bpy.context.scene.camera.rotation_euler[ 1 ] = rotation.y * ( math.pi / 180.0 )
        bpy.context.scene.camera.rotation_euler[ 2 ] = rotation.z * ( math.pi / 180.0 )

    head, basename = os.path.split( infile )

    objects = []
    for i in range( 0, parts ):
        filepath = infile + ( '_%d.obj' % i )

        bpy.ops.import_scene.obj( filepath = filepath )
        objects.append( bpy.context.selected_objects[ 0 ] )

    if verbose:
        print( 'adding %d meshes to simulation' % len( objects ) )

    set_physics_parameters( solver_iterations=1000, steps_per_second=60, time_scale=1.0, use_split_impulse=False, gravity=Vector( ( 0, 0, -9.81 ) ) )

    # add the meshes to the blender scene
    count = 0
    for o in objects:
        mat = add_material( object=o )

        select_objects( o )
        bpy.ops.rigidbody.objects_add( type = 'ACTIVE' )
        o.rigid_body.collision_shape = 'MESH'
        o.rigid_body.mesh_source = 'BASE'
        o.rigid_body.use_margin = True
        o.rigid_body.collision_margin = 0.05
        o.rigid_body.friction = 0.5
        o.rigid_body.restitution = 0.1
        o.rigid_body.linear_damping = 0.0
        o.rigid_body.angular_damping = 0.0
        o.rigid_body.mass = 1.0

    # select the default cube and transform it so that is makes a floor of 1000x1000
    # we assume units to be millimeters, so this gives a sufficiently large floor
    # for real world objects smaller than say 0.5 m.
    cube = bpy.data.objects[ 'Cube' ]
    select_objects( cube )
    cube.location = Vector( ( 0, 0, -1.0 ) )
    cube.scale = Vector( ( 1000, 1000, 1 ) )
    # create a rigid body for it with maximum friction
    bpy.ops.rigidbody.objects_add( type = 'PASSIVE' )
    cube.rigid_body.collision_shape = 'MESH'
    cube.rigid_body.mesh_source = 'BASE'
    cube.rigid_body.use_margin = True
    cube.rigid_body.collision_margin = 0.05
    cube.rigid_body.friction = 0.5
    cube.rigid_body.restitution = 0.1
    cube.rigid_body.linear_damping = 0.0
    cube.rigid_body.angular_damping = 0.0
    cube.rigid_body.mass = 1.0

    # set the visualisation parameters if a movie is made
    if movie:
        #calculate the union of all bounding boxes in world space
        bounds = calculate_world_bounds( objects )
        bounds_size = Vector()
        bounds_size.x = ( bounds[ 1 ] - bounds[ 0 ] )
        bounds_size.y = ( bounds[ 3 ] - bounds[ 2 ] )
        bounds_size.z = ( bounds[ 5 ] - bounds[ 4 ] )

        # position the objects so far away from the floor
        # that we can rotate the model safely without touching or penetrating the floor
        radius = 10 + 0.5 * math.sqrt( bounds_size[ 0 ]**2 + bounds_size[ 1 ]**2 + bounds_size[ 2 ]**2 )

        add_lamp( location=Vector( ( 0, 0, radius ) ) )
        set_render_parameters( frame_end=args.frames - 1 )
        set_camera_parameters()
        set_camera_look_at( eye=Vector( ( 0, -radius, radius ) ), center=Vector( ( 0, 0, 0 ) ) )

    # this seed makes us start with an orientation that is not trivial
    seed( 3 )

    # create output directories
    mkdir_p( '%s' % outdir )
    mkdir_p( '%s/%s' % ( outdir, basename ) )

    # dump a blender file if requested
    if blendfile:
        bpy.ops.wm.save_as_mainfile( filepath='%s/%s/%s.blend' % ( outdir, basename, basename ), check_existing=False )

    # redirect output to log file if not verbose
    if not verbose:
        logfile = '%s/%s/blender_render.log' % ( outdir, basename )
        open( logfile, 'a').close()
        old = os.dup( 1 )
        sys.stdout.flush()
        os.close( 1 )
        os.open( logfile, os.O_WRONLY )

    # run the simulations
    for iter in range( 0, runs ):

        # start from the first frame
        bpy.context.scene.frame_set( 1 )

        # (re)orient the entire assembly for a new run
        a = random() * math.pi * 2.0
        x = ( random() - 0.5 ) * 2.0
        y = ( random() - 0.5 ) * 2.0
        z = ( random() - 0.5 ) * 2.0
        l = math.sqrt( x**2 + y**2 + z**2 )
        rotate_mat = Matrix.Rotation( a, 4, Vector( ( x / l, y / l, z / l ) ) )
        # rotate each mesh around the center of the assembly
        for o in objects:
            o.matrix_world = rotate_mat * o.matrix_world

        #calculate the union of all bounding boxes in world space
        bounds = calculate_world_bounds( objects )

        # make sure lowest point is 10mm above floor
        offset = 10 + math.fabs( min( 0.0, bounds[ 4 ] ) )
        center_mat = Matrix.Translation( Vector( ( 0, 0, offset ) ) )
        for o in objects:
            o.matrix_world = center_mat * o.matrix_world

        bpy.context.scene.update()

        for f in range( 1, frames ):
            bpy.context.scene.frame_set( f )
            if verbose:
                print( 'simulating run %d/%d frame %d/%d' % (iter + 1, runs, f, frames) )

        if movie:
            #Render results
            bpy.context.scene.frame_set( 1 )
            bpy.context.scene.render.filepath = '%s/%s/run_%04d.avi' % ( outdir, basename, iter + 1 )
            bpy.ops.render.render( animation = True )
            if verbose:
                print( 'wrote movie:' + bpy.context.scene.render.filepath )

    # disable output redirection
    if not verbose:
        os.close( 1 )
        os.dup( old )
        os.close( old )

if __name__ == '__main__':
    print( 'using blender version: ' + bpy.app.version_string )

    parser = argparse.ArgumentParser(description='Runs physical simulations of the input object over several runs, and writes the result of each run as a separate obj file. The input geometry is first split into separate parts by using trimesh.split(), randomly rotated along a random axis and lifted at least 10 units above a simulated floor with high friction. For each run of the given number of frames the resulting geometry is written out as a new .obj file.')
    parser.add_argument('infile', default='./input',
                        help='input filename' )
    parser.add_argument('parts', type=int, default=1,
                        help='number of parts with pattern infile_%%d_.obj' )
    parser.add_argument('outdir', default='./output',
                        help='output directory, will be created if non-existent' )
    parser.add_argument('-runs', type=int, default=10,
                        help='specifies the number of simulations from random oriented input geometries are performed and thus determines the number of output files' )
    parser.add_argument('-frames', type=int, default=500,
                        help='specifies the number of frames that each simulation should run. the framerate is 60 fps, so 60 frames represent a simulation of 1 second with the spatial unit being millimeters.' )
    parser.add_argument('-movie', action='store_true', default=False,
                        help='if set, a movie is produced in the output directory' )
    parser.add_argument('-verbose', action='store_true', default=False,
                        help='if set, progress is reported via stdout. If not set, a rendering logfile is created in the output directory' )
    parser.add_argument('-blendfile', action='store_true', default=False,
                        help='if set, a .blend file is generated' )
    args = parser.parse_args()

    simulate( infile=args.infile, 
                parts=args.parts,
                outdir=args.outdir, 
                runs=args.runs, 
                frames=args.frames, 
                movie=args.movie, 
                verbose=args.verbose, 
                blendfile=args.blendfile )
