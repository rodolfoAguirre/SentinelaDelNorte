// Descripcion: adapta el contrato del evaluador web 1.1.0
// Autores: Rodolfo Aguirre Revilla, Leandro Lizama Leirana, Andres Maiztegui Martinez | Matriculas: A00839754, A00840242, A01833484
// Modificacion: 2026-10-21

#pragma once

#include "protocol.h"

namespace grader {
using Json = wire::Json;
using JsonArray = Json::Array;
using JsonObject = Json::Object;

// Calcula un bosque con los campos nodes y weight del evaluador
// Parametro input: nodos y enlaces del caso
// Retorno: costo y enlaces seleccionados como ternas
inline Json mst(const Json &input) {
	engine::Graph graph{int(input.at("nodes").array().size()), {}};
	for (const auto &edge : input.at("edges").array()) {
		graph.edges.push_back(
		    {edge.at("u").integer(), edge.at("v").integer(), edge.at("weight").number()});
	}

	auto result = engine::kruskal(graph, 5000);
	JsonArray edges{};
	for (int index : result.edges) {
		const auto &edge = graph.edges[index];
		edges.emplace_back(JsonArray{edge.sourceNode, edge.targetNode, edge.weight});
	}

	return JsonObject{{"cost", result.cost}, {"edges", edges}};
}

// Resuelve un tour sobre la matriz de distancias recibida
// Parametro input: matriz simetrica sin topologia fisica
// Retorno: costo y ruta cerrada desde el nodo cero
inline Json tsp(const Json &input) {
	const auto &rows = input.at("distances").array();
	int nodeCount = int(rows.size());
	if (nodeCount < 1 || nodeCount > 500) {
		throw std::runtime_error("Distance matrix requires 1..500 nodes");
	}

	std::vector<std::vector<double>> distances{};
	for (const auto &row : rows) {
		if (int(row.array().size()) != nodeCount) {
			throw std::runtime_error("Distance matrix must be square");
		}

		std::vector<double> values{};
		for (const auto &value : row.array()) {
			double distance = value.number();
			if (distance < 0 || distance > 1e12) {
				throw std::runtime_error("Invalid matrix distance");
			}
			values.push_back(distance);
		}
		distances.push_back(values);
	}

	for (int source = 0; source < nodeCount; ++source) {
		for (int target = 0; target < nodeCount; ++target) {
			if (std::abs(distances[source][target] - distances[target][source]) > 1e-9) {
				throw std::runtime_error("Distance matrix must be symmetric");
			}
		}
	}

	std::vector<int> selected(nodeCount);
	std::iota(selected.begin(), selected.end(), 0);
	std::vector<int> route{0, 0};
	int improvements = 0;
	if (nodeCount > 1 && nodeCount <= 16) {
		route = engine::heldKarp(distances, selected);
	} else if (nodeCount > 16) {
		route = engine::heuristicTour(distances, selected, 100, improvements);
	}

	double cost = 0.0;
	for (size_t index = 1; index < route.size(); ++index) {
		cost += distances[route[index - 1]][route[index]];
	}

	return JsonObject{{"cost", cost}, {"route", adapter::integerArray(route)}};
}

// Calcula el flujo dirigido del contrato web
// Parametro input: grafo con capacidades, origen y destino
// Retorno: valor maximo bajo la clave flow
inline Json flow(const Json &input) {
	auto graph = adapter::readGraph(input, "capacity");
	auto result =
	    engine::dinic(graph, input.at("source").integer(), input.at("sink").integer(), true);
	return JsonObject{{"flow", result.value}};
}

// Recorta las regiones usando bounds como dominio
// Parametro input: sitios y limites rectangulares
// Retorno: poligonos bajo la clave cells
inline Json voronoi(const Json &input) {
	std::vector<engine::Point> sites{};
	for (const auto &site : input.at("sites").array()) {
		sites.push_back(adapter::readPoint(site));
	}

	const auto &bounds = input.at("bounds").array();
	adapter::requireCount(bounds, 4, "bounds");
	engine::Box domain{bounds[0].number(), bounds[1].number(), bounds[2].number(),
	                   bounds[3].number()};
	auto result = engine::voronoi(sites, domain, {});
	JsonArray cells{};
	for (const auto &polygon : result.cells) {
		JsonArray vertices{};
		for (auto point : polygon) {
			vertices.emplace_back(JsonArray{point.x, point.y});
		}
		cells.emplace_back(vertices);
	}

	return JsonObject{{"cells", cells}};
}

// Busca una cantidad variable de firmas en dos transmisiones
// Parametro input: textos y lista de patrones
// Retorno: matriz de posiciones base uno o -1 si no hay coincidencia
inline Json matching(const Json &input) {
	const auto &transmissions = input.at("transmissions").array();
	const auto &patterns = input.at("patterns").array();
	adapter::requireCount(transmissions, 2, "transmissions");
	JsonArray matches{};
	for (const auto &transmission : transmissions) {
		JsonArray positions{};
		for (const auto &pattern : patterns) {
			int position = engine::kmp(transmission.str(), pattern.str());
			positions.emplace_back(position < 0 ? -1 : position + 1);
		}
		matches.emplace_back(positions);
	}

	return JsonObject{{"matches", matches}};
}

// Encuentra los dos intervalos de palindromos
// Parametro input: dos transmisiones de texto
// Retorno: intervalos inclusivos base uno bajo ranges
inline Json palindrome(const Json &input) {
	const auto &transmissions = input.at("transmissions").array();
	adapter::requireCount(transmissions, 2, "transmissions");
	JsonArray ranges{};
	for (const auto &transmission : transmissions) {
		auto result = engine::manacher(transmission.str());
		ranges.emplace_back(JsonArray{result.length ? result.start + 1 : 0,
		                              result.length ? result.start + result.length : 0});
	}

	return JsonObject{{"ranges", ranges}};
}

// Calcula el intervalo comun incluso en casos con caracteres no hexadecimales
// Parametro input: dos transmisiones del evaluador
// Retorno: intervalo inclusivo en la primera transmision
inline Json common(const Json &input) {
	const auto &transmissions = input.at("transmissions").array();
	adapter::requireCount(transmissions, 2, "transmissions");
	auto result = engine::longestCommonText(transmissions[0].str(), transmissions[1].str());
	return JsonObject{{"range", JsonArray{result.length ? result.start1 + 1 : 0,
	                                      result.length ? result.start1 + result.length : 0}}};
}

// Despacha el contrato web sin el sobre del adaptador local
// Parametro request: objeto con mode e input
// Retorno: resultado directo del algoritmo
inline Json execute(const Json &request) {
	const auto &mode = request.at("mode").str();
	const auto &input = request.at("input");
	if (mode == "mst") {
		return mst(input);
	}
	if (mode == "tsp") {
		return tsp(input);
	}
	if (mode == "flow") {
		return flow(input);
	}
	if (mode == "voronoi") {
		return voronoi(input);
	}
	if (mode == "matching") {
		return matching(input);
	}
	if (mode == "palindrome") {
		return palindrome(input);
	}
	if (mode == "common") {
		return common(input);
	}

	throw std::runtime_error("Unknown autograder mode: " + mode);
}
}
