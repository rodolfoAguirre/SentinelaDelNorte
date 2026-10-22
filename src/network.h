// Descripcion: resuelve problemas de conectividad y rutas
// Autores: Rodolfo Aguirre Revilla, Leandro Lizama Leirana, Andres Maiztegui Martinez | Matriculas: A00839754, A00840242, A01833484
// Modificacion: 2026-10-21

#pragma once
#include <algorithm>
#include <cmath>
#include <functional>
#include <limits>
#include <numeric>
#include <queue>
#include <stdexcept>
#include <tuple>
#include <vector>

namespace engine {
struct Edge {
	int sourceNode = 0;
	int targetNode = 0;
	double weight = 0.0;
};

struct Graph {
	int nodeCount = 0;
	std::vector<Edge> edges{};
};

// Valida nodos, enlaces y pesos
// Parametro graph: grafo a procesar
// Parametro requireNonnegative: activa la restriccion de pesos no negativos
// Parametro maxNodes: limite de nodos del contrato
// Retorno: sin valor; lanza error si el grafo es invalido
inline void validateGraph(const Graph &graph, bool requireNonnegative = true, int maxNodes = 2000) {
	if (graph.nodeCount < 1 || graph.nodeCount > maxNodes || graph.edges.size() > 200000) {
		throw std::runtime_error("Graph limits: 1.." + std::to_string(maxNodes) +
		                         " nodes, <=200000 edges");
	}

	for (const auto &edge : graph.edges) {
		if (edge.sourceNode < 0 || edge.targetNode < 0 || edge.sourceNode >= graph.nodeCount ||
		    edge.targetNode >= graph.nodeCount || edge.sourceNode == edge.targetNode ||
		    !std::isfinite(edge.weight) || std::abs(edge.weight) > 1e12 ||
		    (requireNonnegative && edge.weight < 0)) {
			throw std::runtime_error(
			    "Invalid edge endpoints/weight (self-loops excluded, |weight|<=1e12)");
		}
	}
}

struct DisjointSet {
	std::vector<int> parents{};
	std::vector<int> sizes{};

	// Inicializa componentes independientes
	// Parametro nodeCount: cantidad de nodos
	// Retorno: instancia con una componente por nodo
	explicit DisjointSet(int nodeCount) : parents(nodeCount), sizes(nodeCount, 1) {
		std::iota(parents.begin(), parents.end(), 0);
	}

	// Busca el representante y comprime el camino
	// Parametro firstNode: primer nodo
	// Retorno: indice del representante
	int findRoot(int firstNode) {
		while (firstNode != parents[firstNode]) {
			parents[firstNode] = parents[parents[firstNode]];
			firstNode = parents[firstNode];
		}

		return firstNode;
	}

	// Une componentes por tamano
	// Parametro firstNode: primer nodo
	// Parametro secondNode: segundo nodo
	// Retorno: true si se unieron componentes distintas
	bool join(int firstNode, int secondNode) {
		firstNode = findRoot(firstNode);
		secondNode = findRoot(secondNode);
		if (firstNode == secondNode) {
			return false;
		}

		if (sizes[firstNode] < sizes[secondNode]) {
			std::swap(firstNode, secondNode);
		}
		parents[secondNode] = firstNode;
		sizes[firstNode] += sizes[secondNode];
		return true;
	}
};

struct SpanningForest {
	std::vector<int> edges{};
	double cost = 0;
	bool connected = false;
	int components = 0;
};

// Construye un bosque de costo minimo
// Parametro graph: grafo a procesar
// Parametro maxNodes: limite de nodos del contrato
// Retorno: enlaces, costo y conectividad
inline SpanningForest kruskal(const Graph &graph, int maxNodes = 2000) {
	validateGraph(graph, false, maxNodes);
	std::vector<int> edgeIndices(graph.edges.size());
	std::iota(edgeIndices.begin(), edgeIndices.end(), 0);

	// Ordena por costo y despues por indice
	// Parametros: firstIndex y secondIndex, enlaces a comparar
	// Retorno: true si el primer enlace precede al segundo
	std::sort(edgeIndices.begin(), edgeIndices.end(), [&](int firstIndex, int secondIndex) {
		return std::tie(graph.edges[firstIndex].weight, firstIndex) <
		       std::tie(graph.edges[secondIndex].weight, secondIndex);
	});
	DisjointSet components(graph.nodeCount);
	SpanningForest result{};
	result.components = graph.nodeCount;
	for (int edgeIndex : edgeIndices) {
		const auto &edge = graph.edges[edgeIndex];
		if (components.join(edge.sourceNode, edge.targetNode)) {
			result.edges.push_back(edgeIndex);
			result.cost += edge.weight;
			--result.components;
		}
	}

	result.connected = result.components == 1;
	return result;
}

struct Tour {
	std::vector<int> order{};
	std::vector<int> physicalNodes{};
	std::vector<int> physicalEdges{};
	double distance = 0;
	bool exact = false;
	int improvements = 0;
};

// Resuelve el tour por subconjuntos
// Parametro distances: distancias desde cada central
// Parametro selected: centrales en orden de entrada
// Retorno: orden exacto de centrales con cierre
inline std::vector<int> heldKarp(const std::vector<std::vector<double>> &distances,
                                 const std::vector<int> &selected) {
	int selectedCount = int(selected.size());
	std::vector<int> tour{};

	// Consulta la distancia entre centrales
	// Parametros: sourceIndex y targetIndex, indices de centrales
	// Retorno: distancia por enlaces existentes
	auto distanceBetween = [&](int sourceIndex, int targetIndex) {
		return distances[sourceIndex][selected[targetIndex]];
	};
	const double INFINITY_DISTANCE = std::numeric_limits<double>::infinity();

	int maskCount = 1 << (selectedCount - 1);
	size_t stateCount = size_t(maskCount) * selectedCount;
	std::vector<double> minimumCosts(stateCount, INFINITY_DISTANCE);
	std::vector<int> predecessors(stateCount, -1);

	// Ubica un estado de la tabla de subconjuntos
	// Parametros: mask, conjunto visitado; centralIndex, ultima central
	// Retorno: indice lineal de la tabla
	auto stateIndex = [&](int mask, int centralIndex) {
		return size_t(mask) * selectedCount + centralIndex;
	};

	for (int centralIndex = 1; centralIndex < selectedCount; ++centralIndex) {
		minimumCosts[stateIndex(1 << (centralIndex - 1), centralIndex)] =
		    distanceBetween(0, centralIndex);
	}

	for (int mask = 1; mask < maskCount; ++mask) {
		for (int centralIndex = 1; centralIndex < selectedCount; ++centralIndex) {
			if (mask & (1 << (centralIndex - 1))) {
				int previousMask = mask ^ (1 << (centralIndex - 1));
				if (previousMask != 0) {
					for (int previousCentral = 1; previousCentral < selectedCount;
					     ++previousCentral) {
						if (previousMask & (1 << (previousCentral - 1))) {
							double candidate =
							    minimumCosts[stateIndex(previousMask, previousCentral)] +
							    distanceBetween(previousCentral, centralIndex);
							if (candidate < minimumCosts[stateIndex(mask, centralIndex)]) {
								minimumCosts[stateIndex(mask, centralIndex)] = candidate;
								predecessors[stateIndex(mask, centralIndex)] = previousCentral;
							}
						}
					}
				}
			}
		}
	}

	int lastCentral = 1;
	for (int centralIndex = 2; centralIndex < selectedCount; ++centralIndex) {
		if (minimumCosts[stateIndex(maskCount - 1, centralIndex)] +
		        distanceBetween(centralIndex, 0) <
		    minimumCosts[stateIndex(maskCount - 1, lastCentral)] +
		        distanceBetween(lastCentral, 0)) {
			lastCentral = centralIndex;
		}
	}

	int mask = maskCount - 1;
	while (lastCentral != -1) {
		tour.push_back(lastCentral);
		int nextCentral = predecessors[stateIndex(mask, lastCentral)];
		mask ^= 1 << (lastCentral - 1);
		lastCentral = nextCentral;
	}

	std::reverse(tour.begin(), tour.end());
	tour.insert(tour.begin(), 0);
	tour.push_back(0);

	return tour;
}

// Mejora un tour mediante intercambios 2-opt
// Parametro distances: distancias desde cada central
// Parametro selected: centrales en orden de entrada
// Parametro maxPasses: limite de pasadas 2-opt
// Parametro improvements: contador de mejoras aceptadas
// Retorno: orden heuristico de centrales con cierre
inline std::vector<int> heuristicTour(const std::vector<std::vector<double>> &distances,
                                      const std::vector<int> &selected, int maxPasses,
                                      int &improvements) {
	int selectedCount = int(selected.size());
	std::vector<int> tour{};

	// Consulta la distancia entre centrales
	// Parametros: sourceIndex y targetIndex, indices de centrales
	// Retorno: distancia por enlaces existentes
	auto distanceBetween = [&](int sourceIndex, int targetIndex) {
		return distances[sourceIndex][selected[targetIndex]];
	};

	std::vector<bool> used(selectedCount);
	used[0] = true;
	tour.push_back(0);
	while (int(tour.size()) < selectedCount) {
		int nextCentral = -1;
		for (int centralIndex = 0; centralIndex < selectedCount; ++centralIndex) {
			if (!used[centralIndex] &&
			    (nextCentral == -1 || distanceBetween(tour.back(), centralIndex) <
			                              distanceBetween(tour.back(), nextCentral))) {
				nextCentral = centralIndex;
			}
		}
		used[nextCentral] = true;
		tour.push_back(nextCentral);
	}
	tour.push_back(0);

	bool hasImprovement = true;
	for (int pass = 0; pass < maxPasses && hasImprovement; ++pass) {
		double gain = 0;
		int segmentStart = -1;
		int segmentEnd = -1;
		for (int firstIndex = 1; firstIndex < selectedCount; ++firstIndex) {
			for (int centralIndex = firstIndex + 1; centralIndex < selectedCount; ++centralIndex) {
				double delta = distanceBetween(tour[firstIndex - 1], tour[firstIndex]) +
				               distanceBetween(tour[centralIndex], tour[centralIndex + 1]) -
				               distanceBetween(tour[firstIndex - 1], tour[centralIndex]) -
				               distanceBetween(tour[firstIndex], tour[centralIndex + 1]);
				if (delta > gain + 1e-10) {
					gain = delta;
					segmentStart = firstIndex;
					segmentEnd = centralIndex;
				}
			}
		}
		hasImprovement = segmentStart != -1;
		if (hasImprovement) {
			std::reverse(tour.begin() + segmentStart, tour.begin() + segmentEnd + 1);
			++improvements;
		}
	}

	return tour;
}

// Planifica visitas y reconstruye enlaces fisicos
// Parametro graph: grafo a procesar
// Parametro selected: centrales en orden de entrada
// Parametro exactLimit: maximo de centrales para solucion exacta
// Parametro maxPasses: limite de pasadas 2-opt
// Retorno: tour, recorrido y distancia total
inline Tour tsp(const Graph &graph, const std::vector<int> &selected, int exactLimit = 16,
                int maxPasses = 100) {
	validateGraph(graph);
	int selectedCount = int(selected.size());
	if (selectedCount < 1 || selectedCount > 500 || exactLimit < 1 || exactLimit > 18 ||
	    maxPasses < 0 || maxPasses > 1000) {
		throw std::runtime_error(
		    "TSP limits: 1..500 selected, exact_limit 1..18, max_passes 0..1000");
	}

	std::vector<bool> visited(graph.nodeCount);
	for (int targetNode : selected) {
		if (targetNode < 0 || targetNode >= graph.nodeCount || visited[targetNode]) {
			throw std::runtime_error("Invalid or repeated TSP node");
		}
		visited[targetNode] = true;
	}

	std::vector<std::vector<std::pair<int, int>>> adjacency(graph.nodeCount);
	for (int edgeIndex = 0; edgeIndex < int(graph.edges.size()); ++edgeIndex) {
		const auto &edge = graph.edges[edgeIndex];
		adjacency[edge.sourceNode].push_back({edge.targetNode, edgeIndex});
		adjacency[edge.targetNode].push_back({edge.sourceNode, edgeIndex});
	}
	const double INFINITY_DISTANCE = std::numeric_limits<double>::infinity();
	std::vector<std::vector<double>> distances(
	    selectedCount, std::vector<double>(graph.nodeCount, INFINITY_DISTANCE));
	std::vector<std::vector<int>> parent(selectedCount, std::vector<int>(graph.nodeCount, -1)),
	    parentEdges = parent;
	for (int sourceIndex = 0; sourceIndex < selectedCount; ++sourceIndex) {
		auto &sourceDistances = distances[sourceIndex];
		sourceDistances[selected[sourceIndex]] = 0;
		using Item = std::pair<double, int>;
		std::priority_queue<Item, std::vector<Item>, std::greater<Item>> pendingNodes{};
		pendingNodes.push({0, selected[sourceIndex]});
		while (!pendingNodes.empty()) {
			auto [currentDistance, targetNode] = pendingNodes.top();
			pendingNodes.pop();
			if (currentDistance == sourceDistances[targetNode]) {
				for (auto [neighbor, edgeIndex] : adjacency[targetNode]) {
					double candidateDistance = currentDistance + graph.edges[edgeIndex].weight;
					if (candidateDistance < sourceDistances[neighbor]) {
						sourceDistances[neighbor] = candidateDistance;
						parent[sourceIndex][neighbor] = targetNode;
						parentEdges[sourceIndex][neighbor] = edgeIndex;
						pendingNodes.push({candidateDistance, neighbor});
					}
				}
			}
		}

		for (int targetNode : selected) {
			if (!std::isfinite(sourceDistances[targetNode])) {
				throw std::runtime_error("Selected TSP nodes are disconnected");
			}
		}
	}

	// Consulta la distancia entre centrales
	// Parametros: sourceIndex y targetIndex, indices de centrales
	// Retorno: distancia por enlaces existentes
	auto distanceBetween = [&](int sourceIndex, int targetIndex) {
		return distances[sourceIndex][selected[targetIndex]];
	};
	Tour result{};
	result.exact = selectedCount <= exactLimit;
	std::vector<int> tour{};
	if (selectedCount == 1) {
		tour = {0, 0};
	} else if (result.exact) {
		tour = heldKarp(distances, selected);
	} else {
		tour = heuristicTour(distances, selected, maxPasses, result.improvements);
	}

	result.physicalNodes.push_back(selected[0]);
	for (int sourceIndex : tour) {
		result.order.push_back(selected[sourceIndex]);
	}

	for (size_t legIndex = 1; legIndex < tour.size(); ++legIndex) {
		int sourceIndex = tour[legIndex - 1], targetNode = selected[tour[legIndex]];
		result.distance += distanceBetween(sourceIndex, tour[legIndex]);
		std::vector<int> pathNodes{};
		std::vector<int> pathEdges{};
		while (targetNode != selected[sourceIndex]) {
			pathNodes.push_back(targetNode);
			pathEdges.push_back(parentEdges[sourceIndex][targetNode]);
			targetNode = parent[sourceIndex][targetNode];
		}

		result.physicalNodes.insert(result.physicalNodes.end(), pathNodes.rbegin(),
		                            pathNodes.rend());
		result.physicalEdges.insert(result.physicalEdges.end(), pathEdges.rbegin(),
		                            pathEdges.rend());
	}

	return result;
}

struct Flow {
	double value = 0;
	std::vector<double> edgeFlow{};
	std::vector<int> sourceSide{};
};

// Maximiza el flujo mediante niveles residuales
// Parametro graph: grafo a procesar
// Parametro source: nodo de origen
// Parametro sink: nodo de destino
// Parametro directed: indica si los enlaces tienen direccion
// Retorno: flujo total, flujos por enlace y corte
inline Flow dinic(const Graph &graph, int source, int sink, bool directed) {
	validateGraph(graph);
	if (source < 0 || sink < 0 || source >= graph.nodeCount || sink >= graph.nodeCount ||
	    source == sink) {
		throw std::runtime_error("Flow source/sink must be distinct valid nodes");
	}

	struct Arc {
		int targetNode = 0;
		int reverseIndex = 0;
		double residual = 0.0;
	};

	std::vector<std::vector<Arc>> adjacency(graph.nodeCount);
	std::vector<int> originalArcs{};
	for (auto arc : graph.edges) {
		originalArcs.push_back(int(adjacency[arc.sourceNode].size()));
		int forwardIndex = int(adjacency[arc.sourceNode].size()),
		    reverseIndex = int(adjacency[arc.targetNode].size());
		adjacency[arc.sourceNode].push_back({arc.targetNode, reverseIndex, arc.weight});
		adjacency[arc.targetNode].push_back(
		    {arc.sourceNode, forwardIndex, directed ? 0 : arc.weight});
	}

	std::vector<int> level(graph.nodeCount), nextArc(graph.nodeCount);
	Flow result{};
	constexpr double RESIDUAL_EPSILON = 1e-9;

	// Construye niveles de la red residual
	// Parametros: ninguno; usa la red capturada
	// Retorno: true si el destino es alcanzable
	auto buildLevels = [&]() {
		std::fill(level.begin(), level.end(), -1);
		std::queue<int> pendingNodes{};
		level[source] = 0;
		pendingNodes.push(source);
		while (!pendingNodes.empty()) {
			int sourceNode = pendingNodes.front();
			pendingNodes.pop();
			for (auto arc : adjacency[sourceNode]) {
				if (arc.residual > RESIDUAL_EPSILON && level[arc.targetNode] < 0) {
					level[arc.targetNode] = level[sourceNode] + 1;
					pendingNodes.push(arc.targetNode);
				}
			}
		}

		return level[sink] >= 0;
	};

	// Envia flujo por el siguiente nivel residual
	// Parametros: sourceNode, nodo actual; availableFlow, flujo disponible
	// Retorno: flujo enviado al destino
	std::function<double(int, double)> sendFlow = [&](int sourceNode,
	                                                  double availableFlow) -> double {
		if (sourceNode == sink) {
			return availableFlow;
		}

		for (int &arcIndex = nextArc[sourceNode]; arcIndex < int(adjacency[sourceNode].size());
		     ++arcIndex) {
			auto &arc = adjacency[sourceNode][arcIndex];
			if (arc.residual > RESIDUAL_EPSILON && level[arc.targetNode] == level[sourceNode] + 1) {
				double sentFlow = sendFlow(arc.targetNode, std::min(availableFlow, arc.residual));
				if (sentFlow > RESIDUAL_EPSILON) {
					arc.residual -= sentFlow;
					adjacency[arc.targetNode][arc.reverseIndex].residual += sentFlow;
					return sentFlow;
				}
			}
		}

		return 0;
	};

	while (buildLevels()) {
		std::fill(nextArc.begin(), nextArc.end(), 0);
		while (double sentFlow = sendFlow(source, std::numeric_limits<double>::infinity())) {
			result.value += sentFlow;
		}
	}

	for (int arcIndex = 0; arcIndex < int(graph.edges.size()); ++arcIndex) {
		auto arc = graph.edges[arcIndex];
		result.edgeFlow.push_back(arc.weight -
		                          adjacency[arc.sourceNode][originalArcs[arcIndex]].residual);
	}

	for (int arcIndex = 0; arcIndex < graph.nodeCount; ++arcIndex) {
		if (level[arcIndex] >= 0) {
			result.sourceSide.push_back(arcIndex);
		}
	}

	return result;
}
}
