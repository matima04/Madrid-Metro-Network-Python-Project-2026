class LineException(Exception):
    pass

class MetroException(Exception):
    pass


class Line:
    def __init__(self, estaciones: list, tiempos: list[tuple]) -> None:
        """Inicializa una línea de metro."""
        self.estaciones = estaciones
        self.tiempos = tiempos
        self.cerradas = []          # estaciones cerradas en esta línea
        self.tramo_cerrado = None   # tupla (start, finish) o None

    def __str__(self) -> str:
        return " --> ".join(self.estaciones)

    def __contains__(self, e: str) -> bool:
        return e in self.estaciones

    def _incluye_tramo_cerrado(self, idx_start: int, idx_finish: int) -> bool:
        """Comprueba si el recorrido entre dos índices (start < finish) contiene el tramo cerrado."""
        if self.tramo_cerrado is None:
            return False
        a, b = self.tramo_cerrado
        i = self.estaciones.index(a)
        j = self.estaciones.index(b)
        if i > j:
            i, j = j, i
        # El tramo cerrado está dentro del recorrido si i >= idx_start y j <= idx_finish
        return i >= idx_start and j <= idx_finish

    def cost_origin2destination(self, start: str, finish: str, sentido: int = 0) -> int:
        """Calcula el tiempo de viaje en la línea, respetando estaciones cerradas y tramo cerrado."""
        if start not in self or finish not in self:
            raise LineException("La estación no pertenece a la línea")
        if start in self.cerradas or finish in self.cerradas:
            raise LineException("No se puede iniciar o terminar en una estación cerrada")

        pos_inicial = self.estaciones.index(start)
        pos_final = self.estaciones.index(finish)

        if pos_inicial == pos_final:
            return 0

        tiempo = 0
        if pos_inicial < pos_final:
            if self._incluye_tramo_cerrado(pos_inicial, pos_final):
                raise LineException("El recorrido atraviesa un tramo cerrado")
            for j in range(pos_inicial, pos_final):
                tiempo += self.tiempos[j][sentido]
        else:
            # pos_inicial > pos_final
            if self._incluye_tramo_cerrado(pos_final, pos_inicial):
                raise LineException("El recorrido atraviesa un tramo cerrado")
            for j in range(pos_final, pos_inicial):
                tiempo += self.tiempos[j][1 - sentido]
        return tiempo

    def cost_origin2destination_rev(self, start: str, finish: str) -> int:
        """Versión inversa: para línea circular usa sentido contrario."""
        if self.estaciones[0] != self.estaciones[-1]:  # no circular
            return self.cost_origin2destination(start, finish)
        else:
            return self.cost_origin2destination(start, finish, sentido=1)

    def close_station(self, e: str) -> None:
        if e not in self.cerradas:
            self.cerradas.append(e)

    def open_station(self, e: str) -> None:
        if e in self.cerradas:
            self.cerradas.remove(e)

    def get_closed_stations(self) -> list:
        """Devuelve la lista de estaciones cerradas en esta línea."""
        return self.cerradas[:]   # copia

    def close_section(self, start: str, finish: str) -> None:
        if self.tramo_cerrado is not None:
            return   # ya hay un tramo cerrado, no hacer nada
        self.tramo_cerrado = (start, finish)

    def get_close_section(self) -> list:
        if self.tramo_cerrado is None:
            return []
        a, b = self.tramo_cerrado
        i = self.estaciones.index(a)
        j = self.estaciones.index(b)
        if i < j:
            return self.estaciones[i:j+1]
        else:
            return self.estaciones[j:i+1]

    def open_section(self) -> None:
        if self.tramo_cerrado is not None:
            self.tramo_cerrado = None


class Metro:
    def __init__(self) -> None:
        self.lineas: dict[str, Line] = {}
        self.transbordos: dict[str, list[str]] = {}

    def __str__(self) -> str:
        return f"Líneas:\n{self.lineas}\n\nTransbordos:\n{self.transbordos}"

    def add_line(self, line_name: str, line: Line) -> None:
        if line_name in self.lineas:
            raise MetroException(f"La línea {line_name} ya existe en la red")
        self.lineas[line_name] = line
        self.add_connections(line_name)

    def add_connections(self, line_name: str) -> None:
        linea = self.lineas[line_name]
        for estacion in linea.estaciones:          # CORREGIDO: variable singular
            if estacion not in self.transbordos:
                self.transbordos[estacion] = []
            if line_name not in self.transbordos[estacion]:
                self.transbordos[estacion].append(line_name)

    @staticmethod
    def load_metro(file_name_lines: str, file_name_times: str) -> 'Metro':
        """Método estático que construye un Metro desde archivos."""
        metro = Metro()

        # ---- Leer líneas ----
        lineas_estaciones = {}
        with open(file_name_lines, 'r',encoding="utf-8-sig") as f:
            lineas = f.readlines()
            i = 0
            while i < len(lineas):
                linea_actual = lineas[i].strip()
                if 'Línea' in linea_actual or 'Ramal' in linea_actual:
                    nombre_linea = linea_actual
                    i += 1
                    while i < len(lineas) and lineas[i].strip() == '':
                        i += 1
                    if i < len(lineas):
                        estaciones_str = lineas[i].strip()
                        if estaciones_str.endswith('.'):
                            estaciones_str = estaciones_str[:-1]
                        lista_estaciones = [e.strip() for e in estaciones_str.split(',')]
                        lineas_estaciones[nombre_linea] = lista_estaciones
                i += 1

        # ---- Leer tiempos ----
        tiempos_dict = {}
        with open(file_name_times, 'r',encoding="utf-8-sig") as f:
            next(f)   # saltar cabecera
            for linea in f:
                linea = linea.strip()
                if not linea:
                    continue
                partes = linea.split(',')
                if len(partes) != 4:
                    continue
                nombre_linea = partes[0].strip()
                origen = partes[1].strip()
                destino = partes[2].strip()
                tiempo_str = partes[3].strip()
                minutos, segundos = tiempo_str.split(':')
                tiempo_seg = int(minutos) * 60 + int(segundos)
                tiempos_dict[(nombre_linea, origen, destino)] = tiempo_seg

        # ---- Construir objetos Line y añadirlos ----
        for nombre_linea, estaciones in lineas_estaciones.items():
            lista_tiempos = []
            for j in range(len(estaciones) - 1):
                origen = estaciones[j]
                destino = estaciones[j+1]
                t_ida = tiempos_dict.get((nombre_linea, origen, destino), 9999)
                t_vuelta = tiempos_dict.get((nombre_linea, destino, origen), 9999)
                lista_tiempos.append((t_ida, t_vuelta))
            linea_obj = Line(estaciones, lista_tiempos)
            metro.add_line(nombre_linea, linea_obj)

        return metro

    def get_line(self, line_name: str) -> Line:
        if line_name not in self.lineas:
            raise MetroException(f"La línea {line_name} no pertenece a la red de metro")
        return self.lineas[line_name]

    def get_closed_stations(self, line_name: str) -> list:
        """Devuelve la lista de estaciones cerradas de la línea line_name."""
        if line_name not in self.lineas:
            raise MetroException(f"La línea {line_name} no pertenece a la red de metro")
        return self.lineas[line_name].get_closed_stations()

    def get_connections(self, e: str, line_name: str) -> list:
        """Devuelve estaciones de la línea (distintas de e) que permiten transbordo a otra línea."""
        if line_name not in self.lineas:
            raise MetroException(f"La línea {line_name} no existe")
        linea = self.lineas[line_name]
        if e not in linea.estaciones:
            raise MetroException(f"La estación {e} no se encuentra en la línea {line_name}")
        if e in linea.cerradas:
            raise MetroException(f"La estación {e} está cerrada, no se puede hacer transbordo desde ella")

        out = []
        for estacion in linea.estaciones:
            if estacion != e and len(self.transbordos.get(estacion, [])) > 1:
                if estacion not in linea.cerradas:   # la estación de transbordo debe estar abierta
                    out.append(estacion)
        return out

    def get_connections2(self, e: str, line_name1: str, line_name2: str) -> list:
        """Devuelve estaciones de line_name1 (incluyendo e) que tienen transbordo a line_name2."""
        if line_name1 not in self.lineas:
            raise MetroException(f"La línea {line_name1} no existe")
        linea1 = self.lineas[line_name1]
        if e not in linea1.estaciones:
            raise MetroException(f"La estación {e} no se encuentra en la línea {line_name1}")

        out = []
        for estacion in linea1.estaciones:
            if line_name2 in self.transbordos.get(estacion, []) and estacion not in linea1.cerradas:
                out.append(estacion)
        return out

    def origin2destination_transfer(self, start: str, finish: str):
        """Mínimo tiempo con máximo 1 transbordo."""
        if start not in self.transbordos:
            raise MetroException(f"La estación {start} no está en la red de Metro")
        if finish not in self.transbordos:
            raise MetroException(f"La estación {finish} no está en la red de Metro")

        mejor = float('inf')
        lineas_start = self.transbordos[start]
        lineas_finish = self.transbordos[finish]

        for l1 in lineas_start:
            for l2 in lineas_finish:
                if l1 == l2:
                    try:
                        t = self.lineas[l1].cost_origin2destination(start, finish)
                        if t < mejor:
                            mejor = t
                    except LineException:
                        continue
                else:
                    for est in self.get_connections2(start, l1, l2):
                        try:
                            t1 = self.lineas[l1].cost_origin2destination(start, est)
                            t2 = self.lineas[l2].cost_origin2destination(est, finish)
                            total = t1 + 300 + t2
                            if total < mejor:
                                mejor = total
                        except LineException:
                            continue

        return mejor if mejor != float('inf') else None

    def origin2destination_transferN(self, start: str, finish: str, n: int):
        """Mínimo tiempo con máximo n transbordos (recursivo)."""
        if start not in self.transbordos:
            raise MetroException(f"La estación {start} no está en la red de Metro")
        if finish not in self.transbordos:
            raise MetroException(f"La estación {finish} no está en la red de Metro")
        if n < 0:
            return None

        mejor = float('inf')
        lineas_start = self.transbordos[start]

        for linea in lineas_start:
            # Caso directo (sin transbordo)
            try:
                if finish in self.lineas[linea].estaciones:
                    t = self.lineas[linea].cost_origin2destination(start, finish)
                    if t < mejor:
                        mejor = t
            except LineException:
                pass

            # Con transbordo(s)
            if n > 0:
                for estacion in self.lineas[linea].estaciones:
                    if estacion == start:
                        continue
                    # Solo considerar estaciones con transbordo a alguna otra línea
                    if len(self.transbordos.get(estacion, [])) > 1:
                        for linea2 in self.transbordos[estacion]:
                            if linea2 == linea:
                                continue
                            try:
                                t1 = self.lineas[linea].cost_origin2destination(start, estacion)
                            except LineException:
                                continue
                            resto = self.origin2destination_transferN(estacion, finish, n - 1)
                            if resto is not None:
                                total = t1 + 300 + resto
                                if total < mejor:
                                    mejor = total

        return mejor if mejor != float('inf') else None

    # --- Métodos de cierre de estaciones y tramos (Parte 3) ---
    def close_station(self, line_name: str, e: str) -> None:
        if line_name not in self.lineas:
            raise MetroException(f"La línea {line_name} no pertenece a la red de metro")
        if e not in self.lineas[line_name].estaciones:
            raise LineException(f"La estación {e} no pertenece a {line_name}")
        self.lineas[line_name].close_station(e)

    def open_station(self, line_name: str, e: str) -> None:
        if line_name not in self.lineas:
            raise MetroException(f"La línea {line_name} no pertenece a la red de metro")
        if e not in self.lineas[line_name].estaciones:
            raise LineException(f"La estación {e} no pertenece a {line_name}")
        self.lineas[line_name].open_station(e)

    def close_section(self, line_name: str, start: str, finish: str) -> None:
        if line_name not in self.lineas:
            raise MetroException(f"La línea {line_name} no pertenece a la red de metro")
        if start not in self.lineas[line_name].estaciones:
            raise LineException(f"La estación {start} no pertenece a {line_name}")
        if finish not in self.lineas[line_name].estaciones:
            raise LineException(f"La estación {finish} no pertenece a {line_name}")
        self.lineas[line_name].close_section(start, finish)

    def get_close_section(self, line_name: str) -> list:
        if line_name not in self.lineas:
            raise MetroException(f"La línea {line_name} no pertenece a la red de metro")
        return self.lineas[line_name].get_close_section()

    def open_section(self, line_name: str) -> None:
        if line_name not in self.lineas:
            raise MetroException(f"La línea {line_name} no pertenece a la red de metro")
        self.lineas[line_name].open_section()
#A continuación probaremos nuestras clases con algunos EJEMPLOS
#Para la clase Line probamos:
line1 = Line(['Embajadores', 'Lavapiés',  'Sol',  'Callao'],
[(40,38), (103,108), (81,90)])
print(line1)
print(line1.cost_origin2destination('Lavapiés','Callao'))
print(line1.cost_origin2destination('Sol','Embajadores'))
print(line1.cost_origin2destination('Sol','Sol'))
print(line1.__contains__("Sol"))
print(line1._incluye_tramo_cerrado(line1.estaciones.index("Lavapiés"),line1.estaciones.index("Callao")))
print(line1.cost_origin2destination_rev('Sol','Embajadores'))
line1.close_station("Sol")
print(line1.get_closed_stations())
line1.close_section("Lavapiés","Callao")
print(line1.get_close_section())
#Para la clase Metro se prueba a continuación
linea1 = Line(
    ["Cuatro Caminos", "Ríos Rosas", "Iglesia", "Bilbao", "Tribunal", "Gran Vía", "Sol"],
    [(70, 72), (65, 67), (80, 82), (75, 76), (90, 91), (60, 62)])

linea2 = Line(
    ["Sol", "Ópera", "Santo Domingo", "Noviciado", "San Bernardo", "Quevedo", "Canal", "Cuatro Caminos"],
    [(50, 52), (65, 66), (70, 72), (80, 78), (75, 77), (60, 62), (85, 83)])

linea3 = Line(["Embajadores", "Lavapiés", "Sol", "Callao", "Plaza de España", "Ventura Rodríguez", "Argüelles", "Moncloa"],
    [(40, 38), (103, 108), (81, 90), (75, 76), (70, 72), (65, 64), (95, 96)])

linea5 = Line(
    ["Gran Vía", "Callao", "Ópera", "La Latina", "Puerta de Toledo", "Acacias"],
    [(55, 57), (60, 61), (90, 88), (75, 73), (80, 82)])

ramal = Line(
    ["Ópera", "Príncipe Pío"],
    [(120, 118)])
metro=Metro()
metro.add_line("Línea 1", linea1)
metro.add_line("Línea 2", linea2)
metro.add_line("Línea 3", linea3)
metro.add_line("Línea 5", linea5)
metro.add_line("Ramal", ramal)
#Probamos los primeros métodos
print(metro.transbordos["Sol"])
print(metro.get_line("Línea 3"))
print(metro.get_connections("Embajadores", "Línea 3"))
print(metro.origin2destination_transfer("Embajadores", "Moncloa"))
#Probamos el método del apartado final
print(metro.origin2destination_transferN("Embajadores", "Moncloa", 0))
#Probamos los métodos de cerrar estaciones y vemos que funcionan
metro.close_station("Línea 3", "Sol")
print(metro.get_closed_stations("Línea 3"))
print(metro.origin2destination_transferN("Embajadores", "Sol", 0))
metro.close_section("Línea 3", "Lavapiés", "Callao")
print(metro.get_close_section("Línea 3"))
#Para probar load_metro recomendable añadir los ficheros desde sus propios archivos