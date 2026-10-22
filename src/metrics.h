// Descripcion: consulta la memoria del proceso
// Autores: Rodolfo Aguirre Revilla, Leandro Lizama Leirana, Andres Maiztegui Martinez | Matriculas: A00839754, A00840242, A01833484
// Modificacion: 2026-10-22

#pragma once

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <psapi.h>
#elif defined(__linux__) || defined(__APPLE__)
#include <sys/resource.h>
#endif
#ifdef __linux__
#include <fstream>
#include <string>
#endif
namespace adapter {

#ifdef __linux__
// Lee el pico de memoria residente de esta imagen del proceso
// Parametros: ninguno
// Retorno: bytes de VmHWM o -1 si /proc no esta disponible
inline double linuxHighWaterBytes() {
	std::ifstream status("/proc/self/status");
	std::string line{};
	double peakBytes = -1;
	while (peakBytes < 0 && std::getline(status, line)) {
		if (line.rfind("VmHWM:", 0) == 0) {
			peakBytes = std::stod(line.substr(6)) * 1024;
		}
	}

	return peakBytes;
}
#endif

// Consulta el pico de memoria del proceso
// Parametros: ninguno
// Retorno: bytes usados o -1 si no esta disponible
inline double peakProcessBytes() {
#ifdef _WIN32
	PROCESS_MEMORY_COUNTERS info{};
	if (GetProcessMemoryInfo(GetCurrentProcess(), &info, sizeof(info))) {
		return double(info.PeakWorkingSetSize);
	}
#elif defined(__linux__) || defined(__APPLE__)
#ifdef __linux__
	// ru_maxrss se hereda del proceso padre a traves de exec; VmHWM no
	double highWaterBytes = linuxHighWaterBytes();
	if (highWaterBytes >= 0) {
		return highWaterBytes;
	}
#endif
	rusage info{};
	if (getrusage(RUSAGE_SELF, &info) == 0) {
#ifdef __APPLE__
		return double(info.ru_maxrss);
#else
		return double(info.ru_maxrss) * 1024;
#endif
	}
#endif
	return -1;
}
}
