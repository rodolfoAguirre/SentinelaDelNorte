// Descripcion: ejecuta el motor desde la terminal o el autograder
// Autores: Rodolfo Aguirre Revilla, Leandro Lizama Leirana, Andres Maiztegui Martinez | Matriculas: A00839754, A00840242, A01833484
// Modificacion: 2026-10-21

#include "metrics.h"
#include "protocol.h"
#include "autograder.h"
#include <clocale>

// Coordina la ejecucion del programa
// Parametro argumentCount: cantidad de argumentos
// Parametro arguments: argumentos de terminal
// Retorno: codigo de salida del proceso
int main(int argumentCount, char **arguments) {
	std::setlocale(LC_NUMERIC, "C");
	bool textMode = false;
#ifdef SENTINELA_AUTOGRADER
	bool graderMode = true;
#else
	bool graderMode = false;
#endif
	try {
		if (argumentCount == 2 && std::string(arguments[1]) == "--text") {
			textMode = true;
		} else if (argumentCount == 2 && std::string(arguments[1]) == "--autograder") {
			graderMode = true;
		} else if (argumentCount != 1) {
			throw std::runtime_error("Usage: sentinela [--text|--autograder] < request.json");
		}

		std::string input{};
		char buffer[8192]{};
		while (std::cin) {
			std::cin.read(buffer, sizeof(buffer));
			input.append(buffer, size_t(std::cin.gcount()));
			if (input.size() > 64000000) {
				throw std::runtime_error("stdin exceeds 64 MB");
			}
		}

		auto request = wire::Parser(input).run();
		if (textMode && request.at("mode").str() != "strings") {
			throw std::runtime_error("--text requires strings mode");
		}

		auto response = graderMode ? grader::execute(request) : adapter::execute(request);
		if (!graderMode && request.has("metrics") && request.at("metrics").boolean()) {
			double peak = adapter::peakProcessBytes();
			auto &metrics = std::get<wire::Json::Object>(
			    std::get<wire::Json::Object>(response.value).at("metrics").value);
			metrics["peak_process_bytes"] = peak >= 0 ? wire::Json(peak) : wire::Json();
		}

		if (textMode) {
			adapter::textResult(std::cout, response);
		} else {
			wire::dump(std::cout, response);
			std::cout << '\n';
		}

		return 0;
	} catch (const std::exception &error) {
		std::cerr << "sentinela: " << error.what() << '\n';
		if (!textMode) {
			wire::dump(std::cout, adapter::JsonObject{{"ok", false},
			                                          {"error", error.what()},
			                                          {"contract", "provisional-v1"}});
			std::cout << '\n';
		}

		return 1;
	}
}
