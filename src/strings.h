// Analiza transmisiones hexadecimales
// Autores: pendientes | Matriculas: pendientes
// Modificacion: 2026-10-21

#pragma once
#include <algorithm>
#include <array>
#include <limits>
#include <map>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

namespace engine {

struct Interval {
	int start = 0;
	int length = 0;
};

struct Common {
	int start1 = 0;
	int start2 = 0;
	int length = 0;
};

// Valida hexadecimal y omite saltos de linea
// Parametro rawText: secuencia sin normalizar
// Retorno: secuencia normalizada
inline std::string normalizeHex(const std::string &rawText) {
	std::string normalized{};
	normalized.reserve(rawText.size());
	for (char character : rawText) {
		if (character != '\r' && character != '\n') {
			if (!((character >= '0' && character <= '9') ||
			      (character >= 'A' && character <= 'F'))) {
				throw std::runtime_error("Hex input permits only 0-9, A-F, CR and LF");
			}
			normalized += character;
		}
	}

	if (normalized.size() > 2000000) {
		throw std::runtime_error("Hex sequence exceeds 2000000 characters");
	}

	return normalized;
}

// Localiza la primera aparicion del patron
// Parametro text: secuencia de entrada
// Parametro pattern: firma a localizar
// Retorno: inicio base cero o -1 si no aparece
inline int kmp(const std::string &text, const std::string &pattern) {
	if (pattern.empty()) {
		return 0;
	}

	std::vector<int> prefixLengths(pattern.size());
	for (int position = 1, matchedLength = 0; position < int(pattern.size()); ++position) {
		while (matchedLength && pattern[position] != pattern[matchedLength]) {
			matchedLength = prefixLengths[matchedLength - 1];
		}

		if (pattern[position] == pattern[matchedLength]) {
			++matchedLength;
		}
		prefixLengths[position] = matchedLength;
	}

	for (int position = 0, matchedLength = 0; position < int(text.size()); ++position) {
		while (matchedLength && text[position] != pattern[matchedLength]) {
			matchedLength = prefixLengths[matchedLength - 1];
		}

		if (text[position] == pattern[matchedLength]) {
			++matchedLength;
		}

		if (matchedLength == int(pattern.size())) {
			return position - matchedLength + 1;
		}
	}

	return -1;
}

// Busca el mayor palindromo par o impar
// Parametro text: secuencia de entrada
// Retorno: intervalo base cero con menor inicio
inline Interval manacher(const std::string &text) {
	int textLength = int(text.size());
	std::vector<int> oddRadii(textLength), evenRadii(textLength);
	Interval best{};

	// Conserva el palindromo mas largo y mas temprano
	// Parametros: start, inicio; length, longitud
	// Retorno: sin valor; actualiza el mejor intervalo
	auto updateBest = [&](int start, int length) {
		if (length > best.length || (length == best.length && start < best.start)) {
			best = {start, length};
		}
	};

	for (int center = 0, leftBoundary = 0, rightBoundary = -1; center < textLength; ++center) {
		int radius = center > rightBoundary
		                 ? 1
		                 : std::min(oddRadii[leftBoundary + rightBoundary - center],
		                            rightBoundary - center + 1);
		while (center - radius >= 0 && center + radius < textLength &&
		       text[center - radius] == text[center + radius]) {
			++radius;
		}
		oddRadii[center] = radius;
		updateBest(center - radius + 1, 2 * radius - 1);
		if (center + radius - 1 > rightBoundary) {
			leftBoundary = center - radius + 1;
			rightBoundary = center + radius - 1;
		}
	}

	for (int center = 0, leftBoundary = 0, rightBoundary = -1; center < textLength; ++center) {
		int radius = center > rightBoundary
		                 ? 0
		                 : std::min(evenRadii[leftBoundary + rightBoundary - center + 1],
		                            rightBoundary - center + 1);
		while (center - radius - 1 >= 0 && center + radius < textLength &&
		       text[center - radius - 1] == text[center + radius]) {
			++radius;
		}
		evenRadii[center] = radius;
		updateBest(center - radius, 2 * radius);
		if (center + radius - 1 > rightBoundary) {
			leftBoundary = center - radius;
			rightBoundary = center + radius - 1;
		}
	}

	return best;
}

// Convierte un digito hexadecimal en indice
// Parametro character: caracter que se procesa
// Retorno: valor entre 0 y 15
inline int hexIndex(char character) {
	return character <= '9' ? character - '0' : character - 'A' + 10;
}

// Busca el mayor fragmento continuo compartido
// Parametro firstText: primera transmision
// Parametro secondText: segunda transmision
// Retorno: inicios base cero y longitud compartida
inline Common longestCommon(const std::string &firstText, const std::string &secondText) {
	struct State {
		std::array<int, 16> next{};
		int link = -1, matchedLength = 0, minEnd = std::numeric_limits<int>::max();

		// Inicializa transiciones del automata
		// Parametros: ninguno
		// Retorno: estado sin transiciones
		State() {
			next.fill(-1);
		}
	};

	std::vector<State> states{};
	states.reserve(2 * firstText.size() + 1);
	states.emplace_back();
	int lastState = 0;
	for (int firstPosition = 0; firstPosition < int(firstText.size()); ++firstPosition) {
		int symbol = hexIndex(firstText[firstPosition]), currentState = int(states.size());
		states.emplace_back();
		states[currentState].matchedLength = states[lastState].matchedLength + 1;
		states[currentState].minEnd = firstPosition;
		int suffixState = lastState;
		while (suffixState != -1 && states[suffixState].next[symbol] == -1) {
			states[suffixState].next[symbol] = currentState;
			suffixState = states[suffixState].link;
		}

		if (suffixState == -1) {
			states[currentState].link = 0;
		} else {
			int nextState = states[suffixState].next[symbol];
			if (states[suffixState].matchedLength + 1 == states[nextState].matchedLength) {
				states[currentState].link = nextState;
			} else {
				int clone = int(states.size());
				states.push_back(states[nextState]);
				states[clone].matchedLength = states[suffixState].matchedLength + 1;
				states[clone].minEnd = std::numeric_limits<int>::max();
				while (suffixState != -1 && states[suffixState].next[symbol] == nextState) {
					states[suffixState].next[symbol] = clone;
					suffixState = states[suffixState].link;
				}
				states[nextState].link = clone;
				states[currentState].link = clone;
			}
		}
		lastState = currentState;
	}

	std::vector<int> lengthCounts(firstText.size() + 1), lengthOrder(states.size());
	for (const auto &stateIndex : states) {
		++lengthCounts[stateIndex.matchedLength];
	}

	for (size_t firstPosition = 1; firstPosition < lengthCounts.size(); ++firstPosition) {
		lengthCounts[firstPosition] += lengthCounts[firstPosition - 1];
	}

	for (int firstPosition = int(states.size()) - 1; firstPosition >= 0; --firstPosition) {
		lengthOrder[--lengthCounts[states[firstPosition].matchedLength]] = firstPosition;
	}

	for (int firstPosition = int(lengthOrder.size()) - 1; firstPosition > 0; --firstPosition) {
		int stateIndex = lengthOrder[firstPosition], suffixState = states[stateIndex].link;
		states[suffixState].minEnd =
		    std::min(states[suffixState].minEnd, states[stateIndex].minEnd);
	}
	Common best{};
	int stateIndex = 0;
	int matchedLength = 0;
	for (int secondPosition = 0; secondPosition < int(secondText.size()); ++secondPosition) {
		int symbol = hexIndex(secondText[secondPosition]);
		while (stateIndex && states[stateIndex].next[symbol] == -1) {
			stateIndex = states[stateIndex].link;
			matchedLength = states[stateIndex].matchedLength;
		}

		if (states[stateIndex].next[symbol] != -1) {
			stateIndex = states[stateIndex].next[symbol];
			++matchedLength;
		} else {
			stateIndex = 0;
			matchedLength = 0;
		}

		if (matchedLength) {
			int firstPosition = states[stateIndex].minEnd - matchedLength + 1,
			    secondStart = secondPosition - matchedLength + 1;
			if (matchedLength > best.length ||
			    (matchedLength == best.length &&
			     std::tie(firstPosition, secondStart) < std::tie(best.start1, best.start2))) {
				best = {firstPosition, secondStart, matchedLength};
			}
		}
	}

	return best;
}

// Amplia el automata para los textos generales del evaluador
// Parametro firstText: primera transmision
// Parametro secondText: segunda transmision
// Retorno: inicios y longitud con desempate estable
inline Common longestCommonText(const std::string &firstText, const std::string &secondText) {
	// Reconoce el alfabeto hexadecimal del motor
	// Parametro character: caracter a revisar
	// Retorno: indica si pertenece al alfabeto
	auto isHex = [](char character) {
		return (character >= '0' && character <= '9') || (character >= 'A' && character <= 'F');
	};
	if (std::all_of(firstText.begin(), firstText.end(), isHex) &&
	    std::all_of(secondText.begin(), secondText.end(), isHex)) {
		return longestCommon(firstText, secondText);
	}

	struct TextState {
		std::map<char, int> next{};
		int link = -1;
		int length = 0;
		int minEnd = std::numeric_limits<int>::max();
	};

	std::vector<TextState> states(1);
	states.reserve(2 * firstText.size() + 1);
	int lastState = 0;
	for (int position = 0; position < int(firstText.size()); ++position) {
		char symbol = firstText[position];
		int currentState = int(states.size());
		states.emplace_back();
		states[currentState].length = states[lastState].length + 1;
		states[currentState].minEnd = position;
		int suffixState = lastState;
		while (suffixState >= 0 && !states[suffixState].next.count(symbol)) {
			states[suffixState].next[symbol] = currentState;
			suffixState = states[suffixState].link;
		}
		if (suffixState < 0) {
			states[currentState].link = 0;
		} else {
			int nextState = states[suffixState].next.at(symbol);
			if (states[suffixState].length + 1 == states[nextState].length) {
				states[currentState].link = nextState;
			} else {
				int clone = int(states.size());
				states.push_back(states[nextState]);
				states[clone].length = states[suffixState].length + 1;
				states[clone].minEnd = std::numeric_limits<int>::max();
				while (suffixState >= 0 && states[suffixState].next.count(symbol) &&
				       states[suffixState].next.at(symbol) == nextState) {
					states[suffixState].next[symbol] = clone;
					suffixState = states[suffixState].link;
				}
				states[nextState].link = clone;
				states[currentState].link = clone;
			}
		}
		lastState = currentState;
	}

	std::vector<int> counts(firstText.size() + 1);
	std::vector<int> order(states.size());
	for (const auto &state : states) {
		++counts[state.length];
	}
	for (size_t index = 1; index < counts.size(); ++index) {
		counts[index] += counts[index - 1];
	}
	for (int index = int(states.size()) - 1; index >= 0; --index) {
		order[--counts[states[index].length]] = index;
	}
	for (int index = int(order.size()) - 1; index > 0; --index) {
		int state = order[index];
		int parent = states[state].link;
		states[parent].minEnd = std::min(states[parent].minEnd, states[state].minEnd);
	}

	Common best{};
	int currentState = 0;
	int matchedLength = 0;
	for (int position = 0; position < int(secondText.size()); ++position) {
		char symbol = secondText[position];
		while (currentState != 0 && !states[currentState].next.count(symbol)) {
			currentState = states[currentState].link;
			matchedLength = states[currentState].length;
		}
		if (states[currentState].next.count(symbol)) {
			currentState = states[currentState].next.at(symbol);
			++matchedLength;
		} else {
			matchedLength = 0;
		}
		if (matchedLength > 0) {
			int firstStart = states[currentState].minEnd - matchedLength + 1;
			int secondStart = position - matchedLength + 1;
			if (matchedLength > best.length ||
			    (matchedLength == best.length &&
			     std::tie(firstStart, secondStart) < std::tie(best.start1, best.start2))) {
				best = {firstStart, secondStart, matchedLength};
			}
		}
	}

	return best;
}
}
