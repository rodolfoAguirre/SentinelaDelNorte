// Lee y escribe el contrato JSON
// Autores: pendientes | Matriculas: pendientes
// Modificacion: 2026-10-21

#pragma once

#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <variant>
#include <vector>

namespace wire {
struct Json {
	using Array = std::vector<Json>;
	using Object = std::map<std::string, Json>;
	std::variant<std::nullptr_t, bool, double, std::string, Array, Object> value;

	// Inicializa un valor del contrato JSON
	// Parametros: ninguno
	// Retorno: instancia con el valor indicado
	Json() : value(nullptr) {}

	// Inicializa un valor del contrato JSON
	// Parametro inputValue: valor inicial
	// Retorno: instancia con el valor indicado
	Json(bool inputValue) : value(inputValue) {}

	// Inicializa un valor del contrato JSON
	// Parametro inputValue: valor inicial
	// Retorno: instancia con el valor indicado
	Json(int inputValue) : value(double(inputValue)) {}

	// Inicializa un valor del contrato JSON
	// Parametro inputValue: valor inicial
	// Retorno: instancia con el valor indicado
	Json(double inputValue) : value(inputValue) {}

	// Inicializa un valor del contrato JSON
	// Parametro inputValue: valor inicial
	// Retorno: instancia con el valor indicado
	Json(const char *inputValue) : value(std::string(inputValue)) {}

	// Inicializa un valor del contrato JSON
	// Parametro inputValue: valor inicial
	// Retorno: instancia con el valor indicado
	Json(std::string inputValue) : value(std::move(inputValue)) {}

	// Inicializa un valor del contrato JSON
	// Parametro inputValue: valor inicial
	// Retorno: instancia con el valor indicado
	Json(Array inputValue) : value(std::move(inputValue)) {}

	// Inicializa un valor del contrato JSON
	// Parametro inputValue: valor inicial
	// Retorno: instancia con el valor indicado
	Json(Object inputValue) : value(std::move(inputValue)) {}

	// Consulta el valor como arreglo
	// Parametros: ninguno
	// Retorno: referencia al arreglo validado
	const Array &array() const {
		if (!std::holds_alternative<Array>(value)) {
			throw std::runtime_error("Expected array");
		}

		return std::get<Array>(value);
	}

	// Consulta el valor como objeto
	// Parametros: ninguno
	// Retorno: referencia al objeto validado
	const Object &object() const {
		if (!std::holds_alternative<Object>(value)) {
			throw std::runtime_error("Expected object");
		}

		return std::get<Object>(value);
	}

	// Consulta el valor como cadena
	// Parametros: ninguno
	// Retorno: referencia a la cadena validada
	const std::string &str() const {
		if (!std::holds_alternative<std::string>(value)) {
			throw std::runtime_error("Expected string");
		}

		return std::get<std::string>(value);
	}

	// Consulta el valor como numero
	// Parametros: ninguno
	// Retorno: numero almacenado
	double number() const {
		if (!std::holds_alternative<double>(value)) {
			throw std::runtime_error("Expected number");
		}

		return std::get<double>(value);
	}

	// Consulta el valor como booleano
	// Parametros: ninguno
	// Retorno: booleano almacenado
	bool boolean() const {
		if (!std::holds_alternative<bool>(value)) {
			throw std::runtime_error("Expected boolean");
		}

		return std::get<bool>(value);
	}

	// Valida un entero de 32 bits
	// Parametros: ninguno
	// Retorno: entero almacenado
	int integer() const {
		double numericValue = number();
		if (numericValue != std::floor(numericValue) || std::abs(numericValue) > 2147483647) {
			throw std::runtime_error("Expected 32-bit integer");
		}

		return int(numericValue);
	}

	// Comprueba la presencia de una clave
	// Parametro key: clave del objeto
	// Retorno: true si existe la clave
	bool has(const std::string &key) const {
		return object().count(key) != 0;
	}

	// Consulta una clave obligatoria
	// Parametro key: clave del objeto
	// Retorno: referencia al valor solicitado
	const Json &at(const std::string &key) const {
		auto entry = object().find(key);
		if (entry == object().end()) {
			throw std::runtime_error("Missing field: " + key);
		}

		return entry->second;
	}
};

class Parser {
	const std::string &sourceText;
	size_t position = 0;

	// Informa la posicion de un error JSON
	// Parametros: ninguno
	// Retorno: sin retorno; lanza una excepcion
	[[noreturn]] void fail() const {
		throw std::runtime_error("Invalid JSON at byte " + std::to_string(position));
	}

	// Avanza sobre espacios permitidos por JSON
	// Parametros: ninguno
	// Retorno: sin valor; actualiza el cursor
	void skipWhitespace() {
		while (position < sourceText.size() &&
		       (sourceText[position] == ' ' || sourceText[position] == '\t' ||
		        sourceText[position] == '\r' || sourceText[position] == '\n')) {
			++position;
		}
	}

	// Consume un delimitador si esta presente
	// Parametro character: caracter que se procesa
	// Retorno: true si encontro el delimitador
	bool take(char character) {
		skipWhitespace();
		if (position < sourceText.size() && sourceText[position] == character) {
			++position;
			return true;
		}

		return false;
	}

	// Lee cuatro digitos de un escape Unicode
	// Parametros: ninguno
	// Retorno: codigo Unicode de 16 bits
	unsigned readHexCode() {
		unsigned numericValue = 0;
		for (int i = 0; i < 4; ++i) {
			if (position == sourceText.size()) {
				fail();
			}
			char character = sourceText[position++];
			numericValue *= 16;
			if (character >= '0' && character <= '9') {
				numericValue += character - '0';
			} else if (character >= 'a' && character <= 'f') {
				numericValue += character - 'a' + 10;
			} else if (character >= 'A' && character <= 'F') {
				numericValue += character - 'A' + 10;
			} else {
				fail();
			}
		}

		return numericValue;
	}

	// Codifica un caracter como UTF-8
	// Parametro decodedText: texto que recibe los bytes
	// Parametro character: caracter que se procesa
	// Retorno: sin valor; agrega bytes al texto
	static void appendUtf8(std::string &decodedText, unsigned character) {
		if (character < 128) {
			decodedText += char(character);
		} else if (character < 2048) {
			decodedText += char(0xc0 | (character >> 6));
			decodedText += char(0x80 | (character & 63));
		} else if (character < 65536) {
			decodedText += char(0xe0 | (character >> 12));
			decodedText += char(0x80 | ((character >> 6) & 63));
			decodedText += char(0x80 | (character & 63));
		} else {
			decodedText += char(0xf0 | (character >> 18));
			decodedText += char(0x80 | ((character >> 12) & 63));
			decodedText += char(0x80 | ((character >> 6) & 63));
			decodedText += char(0x80 | (character & 63));
		}
	}

	// Decodifica un escape JSON
	// Parametros: ninguno
	// Retorno: texto del escape validado
	std::string decodeEscape() {
		switch (sourceText[position++]) {
		case '"':
			return std::string(1, '"');
		case '\\':
			return std::string(1, '\\');
		case '/':
			return std::string(1, '/');
		case 'b':
			return std::string(1, '\b');
		case 'f':
			return std::string(1, '\f');
		case 'n':
			return std::string(1, '\n');
		case 'r':
			return std::string(1, '\r');
		case 't':
			return std::string(1, '\t');
		case 'u': {
			unsigned codePoint = readHexCode();
			if (codePoint >= 0xd800 && codePoint <= 0xdbff) {
				if (position + 2 > sourceText.size() || sourceText[position++] != '\\' ||
				    sourceText[position++] != 'u') {
					fail();
				}
				unsigned element = readHexCode();
				if (element < 0xdc00 || element > 0xdfff) {
					fail();
				}
				codePoint = 0x10000 + ((codePoint - 0xd800) << 10) + (element - 0xdc00);
			} else if (codePoint >= 0xdc00 && codePoint <= 0xdfff) {
				fail();
			}

			std::string decodedText{};

			appendUtf8(decodedText, codePoint);
			return decodedText;
		}
		default:

			fail();
		}
	}

	// Lee una cadena entre comillas
	// Parametros: ninguno
	// Retorno: cadena sin escapes JSON
	std::string string() {
		if (!take('"')) {
			fail();
		}

		std::string decodedText{};
		while (position < sourceText.size()) {
			unsigned char character = sourceText[position++];
			if (character == '"') {
				return decodedText;
			}

			if (character < 32) {
				fail();
			}

			if (character != '\\') {
				decodedText += char(character);
			} else {
				if (position == sourceText.size()) {
					fail();
				}
				decodedText += decodeEscape();
			}
		}

		fail();
	}

	// Interpreta un valor JSON anidado
	// Parametro depth: nivel actual de anidacion
	// Retorno: valor leido desde el cursor
	Json parse(int depth) {
		if (depth > 64) {
			throw std::runtime_error("JSON nesting exceeds 64");
		}

		skipWhitespace();
		if (position == sourceText.size()) {
			fail();
		}
		char character = sourceText[position];
		if (character == '"') {
			return string();
		}

		if (take('{')) {
			Json::Object objectValues{};
			if (take('}')) {
				return objectValues;
			}
			do {
				std::string key = string();
				if (!take(':')) {
					fail();
				}
				Json element = parse(depth + 1);
				if (!objectValues.emplace(key, std::move(element)).second) {
					throw std::runtime_error("Duplicate JSON key: " + key);
				}
			} while (take(','));
			if (!take('}')) {
				fail();
			}

			return objectValues;
		}

		if (take('[')) {
			Json::Array arrayValues{};
			if (take(']')) {
				return arrayValues;
			}
			do {
				arrayValues.push_back(parse(depth + 1));
			} while (take(','));
			if (!take(']')) {
				fail();
			}

			return arrayValues;
		}

		for (auto literal : {"true", "false", "null"}) {
			std::string literalText = literal;
			if (sourceText.compare(position, literalText.size(), literalText) == 0) {
				position += literalText.size();
				if (literalText == "null") {
					return Json();
				}

				return Json(literalText == "true");
			}
		}
		size_t start = position;
		if (sourceText[position] == '-') {
			++position;
		}

		if (position == sourceText.size()) {
			fail();
		}

		if (sourceText[position] == '0') {
			++position;
		} else {
			if (sourceText[position] < '1' || sourceText[position] > '9') {
				fail();
			}

			while (position < sourceText.size() && sourceText[position] >= '0' &&
			       sourceText[position] <= '9') {
				++position;
			}
		}

		if (position < sourceText.size() && sourceText[position] == '.') {
			++position;
			size_t digitsStart = position;
			while (position < sourceText.size() && sourceText[position] >= '0' &&
			       sourceText[position] <= '9') {
				++position;
			}

			if (digitsStart == position) {
				fail();
			}
		}

		if (position < sourceText.size() &&
		    (sourceText[position] == 'e' || sourceText[position] == 'E')) {
			++position;
			if (position < sourceText.size() &&
			    (sourceText[position] == '+' || sourceText[position] == '-')) {
				++position;
			}
			size_t digitsStart = position;
			while (position < sourceText.size() && sourceText[position] >= '0' &&
			       sourceText[position] <= '9') {
				++position;
			}

			if (digitsStart == position) {
				fail();
			}
		}

		double numericValue =
		    std::strtod(sourceText.substr(start, position - start).c_str(), nullptr);
		if (!std::isfinite(numericValue)) {
			fail();
		}

		return numericValue;
	}

  public:
	// Vincula el lector a su texto de entrada
	// Parametro text: secuencia de entrada
	// Retorno: lector con cursor inicial
	explicit Parser(const std::string &text) : sourceText(text) {}

	// Lee un unico objeto y valida el final
	// Parametros: ninguno
	// Retorno: valor JSON sin contenido adicional
	Json run() {
		Json j = parse(0);

		skipWhitespace();
		if (position != sourceText.size()) {
			fail();
		}

		return j;
	}
};

// Serializa un valor JSON
// Parametro output: flujo de salida
// Parametro jsonValue: valor JSON de entrada
// Retorno: sin valor; escribe en el flujo
inline void dump(std::ostream &output, const Json &jsonValue) {
	if (std::holds_alternative<std::nullptr_t>(jsonValue.value)) {
		output << "null";
	} else if (std::holds_alternative<bool>(jsonValue.value)) {
		output << (jsonValue.boolean() ? "true" : "false");
	} else if (std::holds_alternative<double>(jsonValue.value)) {
		if (!std::isfinite(jsonValue.number())) {
			throw std::runtime_error("Nonfinite result");
		}
		output << std::setprecision(17) << jsonValue.number();
	} else if (std::holds_alternative<std::string>(jsonValue.value)) {
		output << '"';
		for (unsigned char character : jsonValue.str()) {
			if (character == '"' || character == '\\') {
				output << '\\' << character;
			} else if (character < 32) {
				output << "\\u" << std::hex << std::setw(4) << std::setfill('0') << int(character)
				       << std::dec;
			} else {
				output << character;
			}
		}
		output << '"';
	} else if (std::holds_alternative<Json::Array>(jsonValue.value)) {
		output << '[';
		bool first = true;
		for (const auto &element : jsonValue.array()) {
			if (!first) {
				output << ',';
			}
			first = false;

			dump(output, element);
		}
		output << ']';
	} else {
		output << '{';
		bool first = true;
		for (const auto &entry : jsonValue.object()) {
			if (!first) {
				output << ',';
			}
			first = false;
			dump(output, Json(entry.first));
			output << ':';
			dump(output, entry.second);
		}
		output << '}';
	}
}
}
