import networkx as nx
from .models import BoomiProcess


def build_graph(process: BoomiProcess) -> nx.DiGraph:
    g = nx.DiGraph()
    for shape in process.shapes:
        g.add_node(shape.id, shape=shape)
    for conn in process.connections:
        if conn.from_shape and conn.to_shape:
            g.add_edge(conn.from_shape, conn.to_shape, connection=conn)
    return g
