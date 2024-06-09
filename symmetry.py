"""
    Mesh components symmetry mapping and beers!
    🍺🍺🍺🍺🍺🍺🍺🍺🍺🍺🍺🍺🍺🍺🍺🍺
"""
import maya.api.OpenMaya as om
import maya.cmds as cmds
from collections import OrderedDict, deque

def _get_face_edges_from_start_edge(mesh, face_index, start_edge_index, reverse=False):
    """
    Get the edges of a face in proper order.
    """
    face_it = om.MItMeshPolygon(mesh)
    face_it.setIndex(face_index)
    
    edges = list(face_it.getEdges())
    
    if start_edge_index not in edges:
        return []
    edge_idx = edges.index(start_edge_index)
    edges = edges[edge_idx:] + edges[:edge_idx]
    
    if reverse:
        # We wanna traverse in opposite direction
        # but still wanna start from the initial edge
        edges = edges[:1] + edges[1:][::-1]
        
    return edges

def get_adjacent_faces_with_edges(mesh, face_index, start_edge_index, reverse=False):
    """
    Get adjacent faces and their connecting edges of a given face index in a mesh starting from a specified edge index.
    Traverses edges in reverse order if reverse is True.
    """
    connected_faces_with_edges = []
    edges = _get_face_edges_from_start_edge(mesh, face_index, start_edge_index, reverse)
    
    for edge_index in edges:
        edge_it = om.MItMeshEdge(mesh)
        edge_it.setIndex(edge_index)
        for adjacent_face_index in edge_it.getConnectedFaces():
            if adjacent_face_index != face_index:
                connected_faces_with_edges.append((adjacent_face_index, edge_index))
    
    return connected_faces_with_edges

def bfs_traverse(mesh, start_left_face, start_right_face, start_left_edge, start_right_edge):
    """
    Perform a bfs traversal from both left and right starting faces.
    """
    left_queue = deque([(start_left_face, start_left_edge)])
    right_queue = deque([(start_right_face, start_right_edge)])
    
    # Dicts are ordered in +3.7, but who know where this spaghetti will run...
    visited_left = OrderedDict()
    visited_right = OrderedDict()
    
    visited_left[start_left_face] = start_left_edge
    visited_right[start_right_face] = start_right_edge
    
    while left_queue and right_queue:
        if left_queue:
            current_face_left, current_edge_left = left_queue.popleft()
            left_adjacents = get_adjacent_faces_with_edges(mesh, current_face_left, current_edge_left, False)
            for left_adj_face, left_adj_edge in left_adjacents:
                if left_adj_face not in visited_left and left_adj_face not in visited_right:
                    visited_left[left_adj_face] = left_adj_edge
                    left_queue.append((left_adj_face, left_adj_edge))
        
        if right_queue:
            current_face_right, current_edge_right = right_queue.popleft()
            right_adjacents = get_adjacent_faces_with_edges(mesh, current_face_right, current_edge_right, True)
            for right_adj_face, right_adj_edge in right_adjacents:
                if right_adj_face not in visited_right and right_adj_face not in visited_left:
                    visited_right[right_adj_face] = right_adj_edge
                    right_queue.append((right_adj_face, right_adj_edge))
        
        # If queues are different length, topology is not symmetrical, and we eject.
        if len(left_queue) != len(right_queue):
            return None
    
    return visited_left, visited_right


def get_faces_mapping(visited_left, visited_right):
    """Getting a little too tipsy to make useful docstrings.
    """
    left_to_right_mapping = {}

    # and comments or that matter, lol
    left_faces = list(visited_left.keys())
    right_faces = list(visited_right.keys())

    for left_face, right_face in zip(left_faces, right_faces):
        left_to_right_mapping[left_face] = right_face

    return left_to_right_mapping

def _get_verts_from_ordered_edges(mesh, edges, face_idx):
    """
    Given a list of edges, return a list of vertices in the correct order.
    """
    face_it = om.MItMeshPolygon(mesh)
    face_it.setIndex(face_idx)
    ordered_vertices = OrderedDict()  

    edge_it = om.MItMeshEdge(mesh)

    edge_it.setIndex(edges[0])
    first_edge_vertices = [edge_it.vertexId(0), edge_it.vertexId(1)  ]
    
    edge_it.setIndex(edges[1])
    second_edge_vertices = [edge_it.vertexId(0), edge_it.vertexId(1)  ]

    if first_edge_vertices[0] not in second_edge_vertices:
        ordered_vertices[first_edge_vertices[0]] = None
    else:
        ordered_vertices[first_edge_vertices[1]] = None

    ordered_vertices[first_edge_vertices[0]] = None
    ordered_vertices[first_edge_vertices[1]] = None

    for edge_index in edges[1:]:
        edge_it.setIndex(edge_index)
        edge_vertices = [edge_it.vertexId(0), edge_it.vertexId(1)]
        for vertex in edge_vertices:
            if vertex not in ordered_vertices:
                ordered_vertices[vertex] = None

    return list(ordered_vertices.keys())


def get_component_mapping(mesh, component_type, visited_left, visited_right):
    """
        Maps the left side to the ride side of components
    """
    left_to_right = {}
    for left_face, right_face in zip(visited_left, visited_right):
        left_edge = visited_left[left_face]
        left_components = _get_face_edges_from_start_edge(mesh, left_face, left_edge, False)
        
        right_edge = visited_right[right_face]        
        right_components = _get_face_edges_from_start_edge(mesh, right_face, right_edge, True)
        
        if component_type == "verts":
            left_components = _get_verts_from_ordered_edges(mesh, left_components, left_face)
            right_components = _get_verts_from_ordered_edges(mesh, right_components, right_face)
        
        for i in range(len(left_components)):
            left_to_right[left_components[i]] = right_components[i]
    return left_to_right

        
    
def main():
    """ This function does the thing!
    """
    selection = cmds.ls(selection=True, fl=True)
    if not (len(selection) == 1 and ".e[" in selection[0]):
        cmds.warning("Please select a single edge")
        return
    
    # Get the selected edge
    edge_name = selection[0]
    selection_list = om.MSelectionList()
    selection_list.add(edge_name)
    edge_path, edge_component = selection_list.getComponent(0)
    
    # Initialize the edge iterator
    edge_it = om.MItMeshEdge(edge_path, edge_component)
    edge_index = edge_it.index()
    
    # Get the faces connected to the selected edge
    connected_faces = edge_it.getConnectedFaces()
    if len(connected_faces) != 2:
        raise RuntimeError("Selected edge is not connected to exactly two faces.")
    
    left_face_index, right_face_index = connected_faces
    
    # Traverse the mesh starting from each face
    mesh_fn = om.MFnMesh(edge_path)
    
    result = bfs_traverse(mesh_fn.object(), left_face_index, right_face_index, edge_index, edge_index)
    if not result:
        cmds.warning("Could not define symmetry.")
        return
    
    visited_left, visited_right = result    
    
    # I am not quite sure if the mapping is always left to right...
    # .... I could query transforms of the initial two faces and sort accordingly, but I am running out of steam and beer... ¯\_(ツ)_/¯
    faces_mapping = get_faces_mapping(visited_left, visited_right)
    edge_mapping = get_component_mapping(mesh_fn.object(), 'Blablabla', visited_left, visited_right)
    vert_mapping = get_component_mapping(mesh_fn.object(), 'verts', visited_left, visited_right)
    
    return faces_mapping, edge_mapping, vert_mapping