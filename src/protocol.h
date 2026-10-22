// Adapta datos y resultados del motor
// Autores: pendientes | Matriculas: pendientes
// Modificacion: 2026-10-21

#pragma once

#include "geometry.h"
#include "json.h"
#include "network.h"
#include "strings.h"
#include <chrono>
#include <fstream>
#include <iostream>
#include <iterator>

namespace adapter {
using Json = wire::Json;
using JsonObject = Json::Object;
using JsonArray = Json::Array;

// Lee un archivo con limite de tamano
// Parametro path: ruta del archivo
// Retorno: contenido binario del archivo
inline std::string readFile(const std::string &path) {
	std::ifstream inputFile(path, std::ios::binary);
	if (!inputFile) {
		throw std::runtime_error("Cannot open file: " + path);
	}

	std::string contents{};
	char buffer[8192]{};
	while (inputFile) {
		inputFile.read(buffer, sizeof(buffer));
		contents.append(buffer, size_t(inputFile.gcount()));
		if (contents.size() > 64000000) {
			throw std::runtime_error("File exceeds 64 MB");
		}
	}

	if (inputFile.bad()) {
		throw std::runtime_error("File read failed: " + path);
	}

	return contents;
}

// Obtiene una secuencia desde texto o archivo
// Parametro value: valor que se convierte
// Retorno: hexadecimal normalizado
inline std::string readSequence(const Json &value) {
	if (std::holds_alternative<std::string>(value.value)) {
		return engine::normalizeHex(value.str());
	}

	return engine::normalizeHex(readFile(value.at("file").str()));
}

// Transforma el grafo del contrato
// Parametro jsonValue: valor JSON de entrada
// Parametro field: nombre del campo de peso
// Retorno: grafo con el peso solicitado
inline engine::Graph readGraph(const Json &jsonValue, const std::string &field) {
	engine::Graph network{jsonValue.at("n").integer(), {}};
	for (const auto &edge : jsonValue.at("edges").array()) {
		network.edges.push_back(
		    {edge.at("u").integer(), edge.at("v").integer(), edge.at(field).number()});
	}

	return network;
}

// Convierte indices a un arreglo JSON
// Parametro value: valor que se convierte
// Retorno: arreglo de enteros
inline JsonArray integerArray(const std::vector<int> &value) {
	JsonArray values{};
	for (int entry : value) {
		values.emplace_back(entry);
	}

	return values;
}

// Adapta un intervalo a posiciones base uno
// Parametro result: resultado del algoritmo
// Retorno: objeto con inicio, fin y longitud
inline Json intervalResult(engine::Interval result) {
	return JsonObject{{"start", result.length ? result.start + 1 : 0},
	                  {"end", result.length ? result.start + result.length : 0},
	                  {"length", result.length}};
}

// Adapta los intervalos compartidos
// Parametro result: resultado del algoritmo
// Retorno: objeto con posiciones en ambas transmisiones
inline Json commonResult(engine::Common result) {
	return JsonObject{{"start", result.length ? result.start1 + 1 : 0},
	                  {"end", result.length ? result.start1 + result.length : 0},
	                  {"start2", result.length ? result.start2 + 1 : 0},
	                  {"end2", result.length ? result.start2 + result.length : 0},
	                  {"length", result.length}};
}

// Valida y convierte coordenadas planas
// Parametro jsonValue: valor JSON de entrada
// Retorno: punto con dos coordenadas
inline engine::Point readPoint(const Json &jsonValue) {
	const auto &values = jsonValue.array();
	if (values.size() != 2) {
		throw std::runtime_error("Point requires [x,y]");
	}

	return {values[0].number(), values[1].number()};
}

// Valida el numero de entradas
// Parametro values: entradas que se validan
// Parametro expectedCount: cantidad requerida
// Parametro label: nombre para diagnosticos
// Retorno: sin valor; lanza error si no coincide
inline void requireCount(const JsonArray &values, size_t expectedCount, const char *label) {
	if (values.size() != expectedCount) {
		throw std::runtime_error(std::string(label) + " requires " + std::to_string(expectedCount) +
		                         " entries");
	}
}

struct Timing {
	double microseconds = 0;

	// Mide una operacion sin incluir I/O
	// Parametro operation: funcion cuyo tiempo se mide
	// Retorno: resultado de la operacion medida
	template <class F> auto run(F operation) {
		auto started = std::chrono::steady_clock::now();
		auto operationResult = operation();
		auto finished = std::chrono::steady_clock::now();
		microseconds += std::chrono::duration<double, std::micro>(finished - started).count();
		return operationResult;
	}
};

// Adapta una solicitud de arbol minimo
// Parametro input: parametros del modo
// Parametro time: acumulador de tiempo
// Retorno: resultado JSON del bosque
inline Json runMst(const Json &input, Timing &time) {
	auto network = readGraph(input, "cost");

	// Ejecuta el calculo sobre los datos preparados
	// Parametros: ninguno; usa los datos capturados
	// Retorno: resultado del algoritmo
	auto result = time.run([&] { return engine::kruskal(network); });
	return JsonObject{{"connected", result.connected},
	                  {"components", result.components},
	                  {"edge_indices", integerArray(result.edges)},
	                  {"total_cost", result.cost},
	                  {"algorithm", "kruskal"}};
}

// Adapta una solicitud de mantenimiento
// Parametro input: parametros del modo
// Parametro time: acumulador de tiempo
// Retorno: resultado JSON del tour
inline Json runTsp(const Json &input, Timing &time) {
	auto network = readGraph(input, "distance");
	std::vector<int> selected{};
	for (const auto &value : input.at("selected").array()) {
		selected.push_back(value.integer());
	}

	int limit = input.has("exact_limit") ? input.at("exact_limit").integer() : 16,
	    passes = input.has("max_passes") ? input.at("max_passes").integer() : 100;

	// Ejecuta el calculo sobre los datos preparados
	// Parametros: ninguno; usa los datos capturados
	// Retorno: resultado del algoritmo
	auto result = time.run([&] { return engine::tsp(network, selected, limit, passes); });
	return JsonObject{{"tour", integerArray(result.order)},
	                  {"physical_nodes", integerArray(result.physicalNodes)},
	                  {"physical_edge_indices", integerArray(result.physicalEdges)},
	                  {"total_distance", result.distance},
	                  {"exact", result.exact},
	                  {"algorithm", result.exact ? "held_karp" : "nearest_neighbor_2opt"},
	                  {"improvements", result.improvements}};
}

// Adapta una solicitud de flujo maximo
// Parametro input: parametros del modo
// Parametro time: acumulador de tiempo
// Retorno: resultado JSON de flujo y corte
inline Json runFlow(const Json &input, Timing &time) {
	auto network = readGraph(input, "capacity");
	int source = input.at("source").integer(), sink = input.at("sink").integer();
	bool directed = input.at("directed").boolean();

	// Ejecuta el calculo sobre los datos preparados
	// Parametros: ninguno; usa los datos capturados
	// Retorno: resultado del algoritmo
	auto result = time.run([&] { return engine::dinic(network, source, sink, directed); });
	JsonArray flows{};
	for (int index = 0; index < int(result.edgeFlow.size()); ++index) {
		flows.emplace_back(JsonObject{{"edge_index", index}, {"flow", result.edgeFlow[index]}});
	}

	return JsonObject{{"value", result.value},
	                  {"flows", flows},
	                  {"source_side", integerArray(result.sourceSide)},
	                  {"algorithm", "dinic"}};
}

// Adapta una solicitud de regiones
// Parametro input: parametros del modo
// Parametro time: acumulador de tiempo
// Retorno: resultado JSON de celdas y consultas
inline Json runVoronoi(const Json &input, Timing &time) {
	std::vector<engine::Point> sites{};
	std::vector<engine::Point> queries{};
	for (const auto &pointValue : input.at("sites").array()) {
		sites.push_back(readPoint(pointValue));
	}

	if (input.has("queries")) {
		for (const auto &pointValue : input.at("queries").array()) {
			queries.push_back(readPoint(pointValue));
		}
	}
	const auto &bounds = input.at("domain").array();

	requireCount(bounds, 4, "domain");
	engine::Box box{bounds[0].number(), bounds[1].number(), bounds[2].number(), bounds[3].number()};

	// Ejecuta el calculo sobre los datos preparados
	// Parametros: ninguno; usa los datos capturados
	// Retorno: resultado del algoritmo
	auto result = time.run([&] { return engine::voronoi(sites, box, queries); });
	JsonArray cells{};
	for (const auto &polygon : result.cells) {
		JsonArray vertices{};
		for (auto pointValue : polygon) {
			vertices.emplace_back(JsonArray{pointValue.x, pointValue.y});
		}
		cells.emplace_back(vertices);
	}

	return JsonObject{
	    {"cells", cells}, {"nearest", integerArray(result.nearest)}, {"algorithm", "half_planes"}};
}

// Adapta los analisis de transmisiones
// Parametro input: parametros del modo
// Parametro time: acumulador de tiempo
// Parametro mode: modo de analisis solicitado
// Retorno: resultados JSON de los modos solicitados
inline Json runStrings(const Json &input, Timing &time, const std::string &mode) {
	std::vector<std::string> transmissions{};
	std::vector<std::string> patterns{};
	const auto &transmissionValues = input.at("transmissions").array();

	requireCount(transmissionValues, 2, "transmissions");
	for (const auto &entry : transmissionValues) {
		transmissions.push_back(readSequence(entry));
	}

	if (mode == "matching" || mode == "strings") {
		const auto &patternValues = input.at("patterns").array();

		requireCount(patternValues, 3, "patterns");
		for (const auto &entry : patternValues) {
			patterns.push_back(readSequence(entry));
		}
	}
	JsonObject output{};
	if (mode == "matching" || mode == "strings") {

		// Ejecuta el calculo sobre los datos preparados
		// Parametros: ninguno; usa los datos capturados
		// Retorno: resultado del algoritmo
		auto positions = time.run([&] {
			std::vector<int> values{};
			for (const auto &transmission : transmissions) {
				for (const auto &pattern : patterns) {
					values.push_back(engine::kmp(transmission, pattern));
				}
			}

			return values;
		});
		JsonArray matches{};
		for (int index = 0; index < 6; ++index) {
			matches.emplace_back(
			    JsonObject{{"transmission", index / 3 + 1},
			               {"pattern", index % 3 + 1},
			               {"found", positions[index] >= 0},
			               {"position", positions[index] >= 0 ? positions[index] + 1 : 0}});
		}
		output["matches"] = matches;
	}

	if (mode == "palindrome" || mode == "strings") {

		// Ejecuta el calculo sobre los datos preparados
		// Parametros: ninguno; usa los datos capturados
		// Retorno: resultado del algoritmo
		auto result = time.run([&] {
			return std::vector<engine::Interval>{engine::manacher(transmissions[0]),
			                                     engine::manacher(transmissions[1])};
		});
		output["palindromes"] = JsonArray{intervalResult(result[0]), intervalResult(result[1])};
	}

	if (mode == "common_substring" || mode == "strings") {
		// Busca el fragmento compartido sin incluir conversiones
		// Parametros: ninguno; usa las transmisiones capturadas
		// Retorno: intervalos de la subcadena comun
		auto common =
		    time.run([&] { return engine::longestCommon(transmissions[0], transmissions[1]); });

		output["common"] = commonResult(common);
	}

	return output;
}

// Despacha una solicitud del contrato
// Parametro request: solicitud completa
// Retorno: respuesta JSON con estado y resultados
inline Json execute(const Json &request) {
	std::string mode = request.at("mode").str();
	const auto &input = request.at("input");
	input.object();

	Json serializedResult{};
	Timing time{};

	if (mode == "mst") {
		serializedResult = runMst(input, time);
	} else if (mode == "tsp") {
		serializedResult = runTsp(input, time);
	} else if (mode == "max_flow") {
		serializedResult = runFlow(input, time);
	} else if (mode == "voronoi") {
		serializedResult = runVoronoi(input, time);
	} else if (mode == "matching" || mode == "palindrome" || mode == "common_substring" ||
	           mode == "strings") {
		serializedResult = runStrings(input, time, mode);
	} else {
		throw std::runtime_error("Unknown mode: " + mode);
	}

	JsonObject response{
	    {"ok", true}, {"mode", mode}, {"result", serializedResult}, {"contract", "provisional-v1"}};
	if (request.has("metrics") && request.at("metrics").boolean()) {
		response["metrics"] = JsonObject{{"algorithm_us", time.microseconds}};
	}

	return response;
}

// Escribe las nueve lineas de cadenas
// Parametro output: flujo de salida
// Parametro response: respuesta del motor
// Retorno: sin valor; escribe en el flujo
inline void textResult(std::ostream &output, const Json &response) {
	const auto &result = response.at("result");
	for (const auto &match : result.at("matches").array()) {
		if (match.at("found").boolean()) {
			output << "true " << match.at("position").integer() << '\n';
		} else {
			output << "false\n";
		}
	}

	for (const auto &palindrome : result.at("palindromes").array()) {
		output << palindrome.at("start").integer() << ' ' << palindrome.at("end").integer() << '\n';
	}
	output << result.at("common").at("start").integer() << ' '
	       << result.at("common").at("end").integer() << '\n';
}
}
