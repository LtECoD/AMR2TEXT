'''
@Description: In User Settings Edit
@Author: your name
@Date: 2019-08-27 21:08:06
@LastEditTime: 2019-09-12 17:21:32
@LastEditors: Please set LastEditors
'''
import numpy as np
from queue import Queue
from copy import deepcopy

from utils import vocab_index_word
import constants as C


class AMRGraph:
    def __init__(self, amr, grh):
        self.nodes = self._parse_amr(amr)
        self.edges = self._parse_grh(grh)
        self.pos = self._get_pos()

    def _parse_amr(self, amr):
        nodes = amr.strip().split()
        return nodes

    def _parse_grh(self, grh):
        def parse_edge(edge):
            edge = edge[1:-1]
            src, dst, et = edge.split(",")
            return int(src), int(dst), et
        raw_edges = grh.strip().split()
        edges = [parse_edge(e) for e in raw_edges]
        return edges

    def _get_pos(self):
        """计算节点的position，既节点到根节点(0)的最小距离"""
        edge_dict = {}
        for (src, dst, et) in self.edges:
            if et != 'd':
                continue
            if src not in edge_dict:
                edge_dict[src] = []
            edge_dict[src].append(dst)

        shortest_length = np.zeros(len(self.nodes), dtype=np.int)
        shortest_length[0] = 2
        visit = np.zeros(len(self.nodes))
        visit[0] = 1

        node_queue = Queue()
        node_queue.put(0)
        while not node_queue.empty():
            cur_node = node_queue.get()
            cur_length = shortest_length[cur_node]
            if cur_node in edge_dict:
                neighbors = edge_dict[cur_node]
                for n in neighbors:
                    if visit[n] == 0:
                        shortest_length[n] = cur_length + 1
                        node_queue.put(n)
                        visit[n] = 1
                    else:
                        assert shortest_length[n] <= cur_length + 1
        shortest_length[-1] = 1
        return shortest_length.tolist()


class Sentence:
    def __init__(self, snt):
        self.tokens = snt.strip().split()
        self.tokens.insert(0, C.BOS_SYMBOL)
        self.tokens.append(C.EOS_SYMBOL)


class Instance:
    def __init__(self, amr, grh, snt, stadia=1):
        self.amr = AMRGraph(amr, grh)
        self.snt = Sentence(snt)
        self.node_mask = None
        self.token_mask = None
        self.stadia = stadia

    def index(self, vocab, edge_vocab):
        self.indexed_token = []
        for token in self.snt.tokens:
            self.indexed_token.append(vocab_index_word(vocab, token))

        self.indexed_node = []
        for node in self.amr.nodes:
            self.indexed_node.append(vocab_index_word(vocab, node))

        self.graph_pos = self.amr.pos
        self.adj = self.build_adj(len(self.indexed_node), self.amr.edges, edge_vocab, self.stadia)
        # self.adj = np.eye(len(self.indexed_node), len(self.indexed_node), dtype=np.int) * C.SELF_EDGE_ID
        # for (src, dst, et) in self.amr.edges:
        #     self.adj[src, dst] = vocab_index_word(edge_vocab, et)

    def set_id(self, _id):
        self.id = _id

    def build_sample_adj(self, node_num, edges, edge_vocab):
        """build simple adjacent matrix with four edge types"""
        adj = np.eye(node_num, node_num, dtype=np.int) * C.SELF_EDGE_ID
        for (src, dst, et) in edges:
            adj[src, dst] = vocab_index_word(edge_vocab, et)
        return adj

    def build_adj(self, node_num, edges, edge_vocab, stadia):
        def add_directed_edge(root, son, dis):
            if dis > stadia:
                return
            if visit[root, son] == 1:
                return
            visit[root, son] = 1
            if adj[root, son] == 0:
                adj[root, son] = C.DIRECTED_EDGE_ID
            if adj[son, root] == 0:
                adj[son, root] = C.REVERSE_EDGE_ID

            for idx, gson in enumerate(directed_edge_list[son]):
                add_directed_edge(son, gson, 1)
                add_directed_edge(root, gson, dis+1)

        directed_edge_list = [set() for i in range(node_num)]
        adj = np.eye(node_num, node_num, dtype=np.int) * C.SELF_EDGE_ID
        for (src, dst, et) in edges:
            adj[src, dst] = vocab_index_word(edge_vocab, et)
            if adj[src, dst] == C.DIRECTED_EDGE_ID:
                directed_edge_list[src].add(dst)
        visit = np.zeros((node_num, node_num))

        for root in range(node_num):
            for idx, son in enumerate(directed_edge_list[root]):
                add_directed_edge(root, son, 1)
        return adj


def pad_instance(ins, src_len, tgt_len):
    new_ins = deepcopy(ins)
    node_len = len(new_ins.indexed_node)
    pl = src_len - node_len
    new_ins.node_mask = [1] * node_len + [0] * pl
    new_ins.indexed_node.extend([C.PAD_ID] * pl)
    new_ins.graph_pos.extend([0] * pl)
    new_adj = np.eye(src_len, src_len) * C.SELF_EDGE_ID
    new_adj[0: node_len, 0:node_len] = new_ins.adj
    new_ins.adj = new_adj
    token_len = len(new_ins.indexed_token)
    pl = tgt_len - token_len
    new_ins.token_mask = [1] * token_len + [0] * pl
    new_ins.indexed_token.extend([C.PAD_ID] * pl)
    return new_ins
