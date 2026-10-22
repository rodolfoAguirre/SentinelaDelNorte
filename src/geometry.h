// Construye regiones de cercania
// Autores: pendientes | Matriculas: pendientes
// Modificacion: 2026-10-21

#pragma once
#include <cmath>
#include <stdexcept>
#include <vector>

namespace engine {
struct Point {
	double x = 0.0;
	double y = 0.0;
};

struct Box {
	double xMin = 0.0;
	double yMin = 0.0;
	double xMax = 0.0;
	double yMax = 0.0;
};

struct Voronoi {
	std::vector<std::vector<Point>> cells{};
	std::vector<int> nearest{};
};

// Calcula distancia euclidiana al cuadrado
// Parametro firstPoint: primer punto
// Parametro secondPoint: segundo punto
// Retorno: distancia cuadrada entre puntos
inline double squaredDistance(Point firstPoint, Point secondPoint) {
	return (firstPoint.x - secondPoint.x) * (firstPoint.x - secondPoint.x) +
	       (firstPoint.y - secondPoint.y) * (firstPoint.y - secondPoint.y);
}

// Recorta regiones y resuelve consultas de cercania
// Parametro sites: coordenadas de las centrales
// Parametro domain: limites del dominio
// Parametro queries: puntos a consultar
// Retorno: poligonos e indices de sitios cercanos
inline Voronoi voronoi(const std::vector<Point> &sites, Box domain,
                       const std::vector<Point> &queries) {

	// Comprueba finitud y escala de las coordenadas
	// Parametro point: coordenadas a validar
	// Retorno: true si cumple los limites
	auto isValidPoint = [](Point point) {
		return std::isfinite(point.x) && std::isfinite(point.y) && std::abs(point.x) <= 1e7 &&
		       std::abs(point.y) <= 1e7;
	};

	if (sites.empty() || sites.size() > 1000 || queries.size() > 100000 ||
	    !isValidPoint({domain.xMin, domain.yMin}) || !isValidPoint({domain.xMax, domain.yMax}) ||
	    domain.xMin >= domain.xMax || domain.yMin >= domain.yMax) {
		throw std::runtime_error(
		    "Invalid Voronoi domain or size (1..1000 sites, <=100000 queries)");
	}

	for (auto point : sites) {
		if (!isValidPoint(point)) {
			throw std::runtime_error("Invalid site coordinate (absolute maximum 1e7)");
		}
	}

	for (auto point : queries) {
		if (!isValidPoint(point)) {
			throw std::runtime_error("Invalid query coordinate");
		}
	}
	Voronoi result{};
	result.cells.resize(sites.size());
	for (size_t siteIndex = 0; siteIndex < sites.size(); ++siteIndex) {
		auto &polygon = result.cells[siteIndex];
		polygon = {{domain.xMin, domain.yMin},
		           {domain.xMax, domain.yMin},
		           {domain.xMax, domain.yMax},
		           {domain.xMin, domain.yMax}};
		for (size_t otherIndex = 0; otherIndex < sites.size() && !polygon.empty(); ++otherIndex) {
			if (siteIndex != otherIndex) {
				if (sites[siteIndex].x == sites[otherIndex].x &&
				    sites[siteIndex].y == sites[otherIndex].y) {
					if (otherIndex < siteIndex) {
						polygon.clear();
					}
				} else {
					double normalX = sites[otherIndex].x - sites[siteIndex].x,
					       normalY = sites[otherIndex].y - sites[siteIndex].y,
					       normalLength = std::hypot(normalX, normalY);
					normalX /= normalLength;
					normalY /= normalLength;
					Point midpoint{(sites[siteIndex].x + sites[otherIndex].x) / 2,
					               (sites[siteIndex].y + sites[otherIndex].y) / 2};

					// Evalua el semiplano mediante la mediatriz
					// Parametro point: vertice del poligono
					// Retorno: distancia con signo a la frontera
					auto signedDistance = [&](Point point) {
						return normalX * (point.x - midpoint.x) + normalY * (point.y - midpoint.y);
					};

					std::vector<Point> clipped{};
					for (size_t vertexIndex = 0; vertexIndex < polygon.size(); ++vertexIndex) {
						Point firstPoint = polygon[vertexIndex],
						      nextPoint = polygon[(vertexIndex + 1) % polygon.size()];
						double firstDistance = signedDistance(firstPoint),
						       nextDistance = signedDistance(nextPoint);
						bool firstInside = firstDistance <= 0, nextInside = nextDistance <= 0;
						if (firstInside) {
							clipped.push_back(firstPoint);
						}

						if (firstInside != nextInside) {
							double fraction = firstDistance / (firstDistance - nextDistance);
							clipped.push_back(
							    {firstPoint.x + fraction * (nextPoint.x - firstPoint.x),
							     firstPoint.y + fraction * (nextPoint.y - firstPoint.y)});
						}
					}
					polygon = std::move(clipped);
				}
			}
		}
	}

	for (auto query : queries) {
		int nearestIndex = 0;
		for (int candidateIndex = 1; candidateIndex < int(sites.size()); ++candidateIndex) {
			if (squaredDistance(query, sites[candidateIndex]) <

			    squaredDistance(query, sites[nearestIndex])) {
				nearestIndex = candidateIndex;
			}
		}

		result.nearest.push_back(nearestIndex);
	}

	return result;
}
}
