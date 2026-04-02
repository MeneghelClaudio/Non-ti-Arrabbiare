"""
dado.py - Animazione 3D del dado
================================

Gestisce il rendering e l'animazione 3D del dado,
incluse rotazioni, proiezioni e rendering delle facce.
"""

import pygame
import math
import random


# =============================================================================
# COSTANTI DI ANIMAZIONE
# =============================================================================

DEFAULT_THROW_DURATION_MS = 1500    # Durata animazione lancio (millisecondi)
ROT_ROUNDS_MIN = 3                 # Giri minimi durante rotazione
ROT_ROUNDS_MAX = 5                 # Giri massimi durante rotazione
INITIAL_SCALE = 1.5                # Scala iniziale (lontano)
FINAL_SCALE = 0.7                  # Scala finale (vicino)
CAMERA_DISTANCE = 400               # Distanza camera per proiezione

# =============================================================================
# COSTANTI DI STILE
# =============================================================================

DEFAULT_SIZE = 60                  # Dimensione base del dado
FACE_BASE_COLOR = (240, 240, 240)   # Colore base delle facce
FACE_BORDER_COLOR = (30, 30, 30)   # Colore bordo facce
BORDER_THICKNESS = 2               # Spessore bordo
FACE_SHADE_MIN = 80                # Shade minimo per.depth
FACE_SHADE_BASE = 200              # Shade base per.depth

# Puntini
PIP_COLOR = (20, 20, 20)          # Colore puntini
PIP_RADIUS_RATIO = 0.1            # Raggio puntino rispetto alla size
PIP_OFFSET_RATIO = 0.25            # Distanza puntino dal centro
PIP_SEGMENTS = 25                  # Segmenti per disegnare puntino ellittico


class Dado:
    """
    Dado 3D animato per il gioco.
    
    Gestisce:
      - Rendering delle 6 facce con proiezione prospettica
      - Animazione di lancio con rotazioni
      - Disegno dei puntini su ogni faccia
    """
    
    def __init__(self, center_x, center_y, size=DEFAULT_SIZE, color=FACE_BASE_COLOR):
        self.center_x = center_x
        self.center_y = center_y
        self.start_x = center_x
        self.start_y = center_y
        self.target_x = center_x
        self.target_y = center_y
        
        self.size = size
        self.current_size = size
        self.color = color

        # Angoli di rotazione correnti
        self.rot_x = 0.0
        self.rot_y = 0.0
        self.rot_z = 0.0

        # Stato animazione
        self.is_animating = False
        self.anim_time = 0.0
        self.anim_duration = 0.0
        
        self.start_rot = (0, 0, 0)
        self.target_rot = (0, 0, 0)

        # Vertici cubo 3D
        s = size / 2
        self.vertices = [
            [-s, -s, -s], [ s, -s, -s], [ s,  s, -s], [-s,  s, -s],
            [-s, -s,  s], [ s, -s,  s], [ s,  s,  s], [-s,  s,  s],
        ]

        # Facce: vertici + numero (1=retro, 6=fronte, etc.)
        self.faces = [
            ((0, 1, 2, 3), 1),  # back
            ((4, 5, 6, 7), 6),  # front
            ((0, 1, 5, 4), 2),  # top
            ((2, 3, 7, 6), 5),  # bottom
            ((1, 2, 6, 5), 3),  # right
            ((0, 3, 7, 4), 4),  # left
        ]

        # Rotazioni per mostrare la faccia corretta
        pi = math.pi
        self.face_rotations = {
            1: (0, pi, 0),
            2: (pi/2, 0, 0),
            3: (0, -pi/2, 0),
            4: (0, pi/2, 0),
            5: (-pi/2, 0, 0),
            6: (0, 0, 0),
        }

        # Posizioni puntini per ogni faccia
        self.pips = {
            1: [(0, 0)],
            2: [(-0.5, -0.5), (0.5, 0.5)],
            3: [(-0.5, -0.5), (0, 0), (0.5, 0.5)],
            4: [(-0.5, -0.5), (0.5, -0.5), (-0.5, 0.5), (0.5, 0.5)],
            5: [(-0.5, -0.5), (0.5, -0.5), (0, 0), (-0.5, 0.5), (0.5, 0.5)],
            6: [(-0.5, -0.6), (0.5, -0.6), (-0.5, 0),
                (0.5, 0), (-0.5, 0.6), (0.5, 0.6)],
        }

    def lancia(self, esito, start_x, start_y, end_x, end_y, durata_ms=DEFAULT_THROW_DURATION_MS):
        """
        Avvia l'animazione del lancio.
        
        Args:
            esito: valore del dado (1-6)
            start_x, start_y: posizione iniziale
            end_x, end_y: posizione finale
            durata_ms: durata in millisecondi
        """
        self.is_animating = True
        self.anim_time = 0
        self.anim_duration = durata_ms / 1000.0
        
        self.start_x, self.start_y = start_x, start_y
        self.target_x, self.target_y = end_x, end_y
        self.start_rot = (self.rot_x, self.rot_y, self.rot_z)

        # Calcola rotazione finale
        esito = 7 - esito if esito in (1, 3, 4, 6) else esito
        base_target = self.face_rotations.get(esito, (0, 0, 0))
        rounds_x = random.randint(ROT_ROUNDS_MIN, ROT_ROUNDS_MAX) * 2 * math.pi
        rounds_y = random.randint(ROT_ROUNDS_MIN, ROT_ROUNDS_MAX) * 2 * math.pi
        
        self.target_rot = (
            base_target[0] + rounds_x,
            base_target[1] + rounds_y,
            base_target[2]
        )

    def update(self, dt):
        """Aggiorna posizione e rotazione durante l'animazione."""
        if not self.is_animating:
            return

        self.anim_time += dt
        t = min(1.0, self.anim_time / self.anim_duration)

        # Easing: Cubic per posizione, Expo per rotazione
        t_pos = 1 - pow(1 - t, 3)
        t_rot = 1 if t == 1 else 1 - pow(2, -10 * t)
        
        # Scala interpolata
        current_scale = INITIAL_SCALE + (FINAL_SCALE - INITIAL_SCALE) * t_pos
        self.current_size = self.size * current_scale

        # Posizione interpolata
        self.center_x = self.start_x + (self.target_x - self.start_x) * t_pos
        self.center_y = self.start_y + (self.target_y - self.start_y) * t_pos

        # Rotazione interpolata
        self.rot_x = self.start_rot[0] + (self.target_rot[0] - self.start_rot[0]) * t_rot
        self.rot_y = self.start_rot[1] + (self.target_rot[1] - self.start_rot[1]) * t_rot
        self.rot_z = self.start_rot[2] + (self.target_rot[2] - self.start_rot[2]) * t_rot

        if t >= 1.0:
            self.is_animating = False
            # Normalizza angoli per evitare numeri enormi
            self.rot_x %= (2 * math.pi)
            self.rot_y %= (2 * math.pi)
            self.rot_z %= (2 * math.pi)

    def _rotate_vertex(self, v):
        """Applica rotazioni 3D a un vertice."""
        # Applica scala
        scale_factor = self.current_size / self.size
        x, y, z = [coord * scale_factor for coord in v]
        
        # Rotazione X
        cx, sx = math.cos(self.rot_x), math.sin(self.rot_x)
        y, z = y * cx - z * sx, y * sx + z * cx
        # Rotazione Y
        cy, sy = math.cos(self.rot_y), math.sin(self.rot_y)
        x, z = x * cy + z * sy, -x * sy + z * cy
        # Rotazione Z
        cz, sz = math.cos(self.rot_z), math.sin(self.rot_z)
        x, y = x * cz - y * sz, x * sz + y * cz
        
        return [x, y, z]

    def _project(self, v):
        """
        Proiezione prospettica 3D → 2D.
        Più z è grande, più il punto è lontano (più piccolo).
        """
        x, y, z = v
        factor = CAMERA_DISTANCE / (CAMERA_DISTANCE + z)
        return (
            int(x * factor + self.center_x),
            int(y * factor + self.center_y),
        )

    def _draw_ellipse_pip(self, screen, center_3d, u, v, pip_radius):
        """
        Disegna un puntino come ellisse proiettata.
        Usa la superficie della faccia per un effetto più realistico.
        """
        circle_points = []
        for i in range(PIP_SEGMENTS):
            angle = 2 * math.pi * i / PIP_SEGMENTS
            offset_u = math.cos(angle) * pip_radius
            offset_v = math.sin(angle) * pip_radius
            point_3d = [
                center_3d[j] + u[j] * offset_u + v[j] * offset_v
                for j in range(3)
            ]
            circle_points.append(self._project(point_3d))
        
        if len(circle_points) >= 3:
            pygame.draw.polygon(screen, PIP_COLOR, circle_points)

    def draw(self, screen):
        """
        Renderizza il dado 3D sullo schermo.
        Ordina le facce per profondità (painter's algorithm).
        """
        rotated = [self._rotate_vertex(v) for v in self.vertices]
        projected = [self._project(v) for v in rotated]
        
        # Calcola profondità media per ogni faccia
        face_depth = []
        for face, num in self.faces:
            z_avg = sum(rotated[i][2] for i in face) / 4
            face_depth.append((z_avg, face, num))
        
        # Ordina: facce più vicine per ultime (disegnate sopra)
        face_depth.sort(key=lambda x: x[0], reverse=True)

        for z, face, num in face_depth:
            points = [projected[i] for i in face]
            
            # Shading basato su profondità
            shade = max(FACE_SHADE_MIN, min(255, int(FACE_SHADE_BASE - z)))
            color = tuple(min(c, shade) for c in self.color)
            
            # Disegna faccia e bordo
            pygame.draw.polygon(screen, color, points)
            pygame.draw.polygon(screen, FACE_BORDER_COLOR, points, BORDER_THICKNESS)

            # Disegna puntini
            v0, v1, v2, v3 = [rotated[i] for i in face]
            
            center = [
                (v0[0] + v1[0] + v2[0] + v3[0]) / 4,
                (v0[1] + v1[1] + v2[1] + v3[1]) / 4,
                (v0[2] + v1[2] + v2[2] + v3[2]) / 4,
            ]
            
            # Vettori u e v per orientare i puntini sulla faccia
            u = [v1[i] - v0[i] for i in range(3)]
            v = [v3[i] - v0[i] for i in range(3)]
            
            ul = math.sqrt(sum(c * c for c in u))
            vl = math.sqrt(sum(c * c for c in v))
            
            u = [c / ul for c in u] if ul != 0 else u
            v = [c / vl for c in v] if vl != 0 else v
            
            # Disegna ogni puntino
            pip_radius = self.current_size * PIP_RADIUS_RATIO

            for px, py in self.pips[num]:
                pip_center = [
                    center[i] + u[i] * px * self.current_size * (PIP_OFFSET_RATIO / 0.5) +
                    v[i] * py * self.current_size * (PIP_OFFSET_RATIO / 0.5)
                    for i in range(3)
                ]
                self._draw_ellipse_pip(screen, pip_center, u, v, pip_radius)

    def is_finished(self):
        """True se l'animazione è terminata."""
        return not self.is_animating
