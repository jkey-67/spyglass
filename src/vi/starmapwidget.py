import ctypes
import csv
import json
import math
import os
import time
import re
import string
from dataclasses import dataclass
from enum import IntEnum
from typing import Iterable, List, Optional, Tuple
import PySide6.QtCore
import numpy as np
from OpenGL.raw.GL.VERSION.GL_1_0 import GL_LESS, GL_DST_ALPHA, GL_ZERO
from PySide6 import QtCore, QtGui, QtWidgets, QtOpenGLWidgets
from OpenGL.GL import (
    GL_ARRAY_BUFFER,
    GL_BLEND,
    GL_COLOR_BUFFER_BIT,
    GL_COMPILE_STATUS,
    GL_COMPUTE_SHADER,
    GL_DYNAMIC_DRAW,
    GL_DYNAMIC_READ,
    GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST,
    GL_FLOAT,
    GL_FRAGMENT_SHADER,
    GL_GEOMETRY_SHADER,
    GL_LINK_STATUS,
    GL_LINES,
    GL_LINE_SMOOTH,
    GL_LINE_SMOOTH_HINT,
    GL_MULTISAMPLE,
    GL_NICEST,
    GL_ONE,
    GL_ONE_MINUS_CONSTANT_COLOR,
    GL_SRC_ALPHA_SATURATE,
    GL_DST_COLOR,
    GL_ONE_MINUS_DST_COLOR,
    GL_ONE_MINUS_SRC_ALPHA,
    GL_SRC_ALPHA,
    GL_POLYGON_OFFSET_FILL,
    GL_PROGRAM_POINT_SIZE,
    GL_RGBA,
    GL_SHADER_STORAGE_BARRIER_BIT,
    GL_SHADER_STORAGE_BUFFER,
    GL_CLAMP_TO_EDGE,
    GL_LINEAR,
    GL_LINEAR_MIPMAP_LINEAR,
    GL_STATIC_DRAW,
    GL_TEXTURE0,
    GL_TEXTURE_2D,
    GL_TEXTURE_MAG_FILTER,
    GL_TEXTURE_MIN_FILTER,
    GL_TEXTURE_WRAP_S,
    GL_TEXTURE_WRAP_T,
    GL_TRIANGLE_STRIP,
    GL_TRIANGLES,
    GL_UNSIGNED_BYTE,
    GL_VERTEX_SHADER,
    glActiveTexture,
    glAttachShader,
    glBindBuffer,
    glBindBufferBase,
    glBindVertexArray,
    glBlendFunc,
    glBlendFuncSeparate,
    glBufferData,
    glClear,
    glClearColor,
    glCompileShader,
    glCreateProgram,
    glCreateShader,
    glDeleteBuffers,
    glDeleteVertexArrays,
    glDeleteProgram,
    glDeleteShader,
    glDrawArrays,
    glDrawArraysInstanced,
    glDispatchCompute,
    glDisable,
    glEnable,
    glHint,
    glEnableVertexAttribArray,
    glGetBufferSubData,
    glGetProgramInfoLog,
    glGetProgramiv,
    glGetShaderInfoLog,
    glGetShaderiv,
    glGetUniformLocation,
    glGenerateMipmap,
    glLinkProgram,
    glShaderSource,
    glTexImage2D,
    glTexParameteri,
    glUniformMatrix4fv,
    glUniform1i,
    glUniform1f,
    glUniform2f,
    glUniform3f,
    glUniform4f,
    glUseProgram,
    glVertexAttribPointer,
    glVertexAttribDivisor,
    glGenBuffers,
    glGenVertexArrays,
    glGenTextures,
    glBindTexture,
    glViewport,
    glDepthFunc,
    glPolygonOffset,
    glMemoryBarrier,
)


class IntelStatus(IntEnum):
    """Enumerate intel status values used for label coloring.

    Attributes:
        NONE: No intel state.
        GREEN: Friendly/green intel state.
        RED: Hostile/red intel state.
    """

    NONE = 0
    GREEN = 1
    RED = 2


@dataclass(frozen=False)
class System:
    """Represents a solar system with renderable position and metadata.

    Attributes:
        x: Normalized X coordinate in map space.
        y: Normalized Y coordinate in map space.
        z: Normalized Z coordinate in map space (unused in 2D render).
        name_en: Localized system name used for labels and lookups.
        status: Status text displayed on the second label line.
        sec_state: Security state indicator rendered above the label.
        statistics: Statistic text rendered below the label.
        timer: Timer text rendered above the label on the right.
        marked: Remaining mark timer in milliseconds driving halo fade-out.
        killed: Remaining kill timer in milliseconds driving halo fade-out.
        intel_status: Intel status enum indicating a red or green alert state.
        intel_status_time: UTC timestamp (float seconds) when intel was recorded.
        monitored: Flag for halo rendering when system is monitored.
        populated: Flag for halo rendering when system is populated.
        contested: Flag for halo rendering when a system is contested (red).
        incursion: Flag for halo rendering when under incursion (yellow).
        structure: Structure type indicator (0 = none, 1/2/3 = small/medium/large).
        system_id: Unique numeric identifier for stargate linkage.
        record: Raw record dictionary from the source dataset.
        honeycomb_color: RGBA tuple controlling the honeycomb fill color.
        honeycomb_margin: Extra pixel margin added around the label for the honeycomb.
    """
    x: float
    y: float
    z: float
    name_en: str
    status: str
    sec_state: str
    statistics: str
    timer: str
    marked: int
    killed: int
    intel_status: IntelStatus
    intel_status_time: float
    monitored: int
    populated: int
    contested: int
    incursion: int
    structure: int
    system_id: int
    record: dict
    honeycomb_color: Tuple[float, float, float, float] = (0.16, 0.2, 0.23, 1.0)
    honeycomb_margin: float = 8.0


@dataclass(frozen=True)
class ConnectionLineGroups:
    """Grouped connection vertices for multi-color rendering.

    Attributes:
        standard: Base connection line vertices.
        cross_constellation: Connection vertices crossing constellation borders.
        cross_region: Connection vertices crossing region borders.
    """

    standard: np.ndarray
    cross_constellation: np.ndarray
    cross_region: np.ndarray

    @property
    def size(self) -> int:
        """Return the total number of float components in all groups.

        Returns:
            Total float count across `standard`, `cross_constellation`, and `cross_region`.
        """
        return int(self.standard.size + self.cross_constellation.size + self.cross_region.size)


VERT_SHADER = """
#version 460 core
layout (location = 0) in vec3 aPos;

uniform mat4 uView;
uniform mat4 uProj;

out float vDepth;

void main() {
    vec4 viewPos = uView * vec4(aPos, 1.0);
    gl_Position = uProj * viewPos;
    float dist = length(viewPos.xyz);
    gl_PointSize = clamp(6.0 / (1.0 + dist), 1.5, 6.0);
    vDepth = dist;
}
"""

FRAG_SHADER = """
#version 460 core
in float vDepth;
out vec4 FragColor;

void main() {
    vec2 uv = gl_PointCoord * 2.0 - 1.0;
    float d = dot(uv, uv);
    float alpha = smoothstep(1.0, 0.3, d);
    vec3 color = mix(vec3(1.0, 0.95, 0.9), vec3(0.6, 0.7, 1.0), clamp(vDepth / 10.0, 0.0, 1.0));
    FragColor = vec4(color, alpha);
}
"""

LINE_VERT_SHADER = """
#version 460 core
layout (location = 0) in vec3 aPos;

uniform mat4 uView;
uniform mat4 uProj;

void main() {
    gl_Position = uProj * uView * vec4(aPos, 1.0);
}
"""

LINE_FRAG_SHADER = """
#version 460 core
out vec4 FragColor;

uniform vec3 uColor;

void main() {
    FragColor = vec4(uColor, 1.0);
}
"""

LINE_GEOM_SHADER = """
#version 460 core
layout (lines) in;
layout (triangle_strip, max_vertices = 4) out;

uniform vec2 uScreen;
uniform float uLineThickness;

vec4 offset_clip(vec4 clip_pos, vec2 ndc_offset) {
    return vec4(ndc_offset * clip_pos.w, 0.0, 0.0);
}

void main() {
    vec4 p0 = gl_in[0].gl_Position;
    vec4 p1 = gl_in[1].gl_Position;

    vec2 p0_ndc = p0.xy / p0.w;
    vec2 p1_ndc = p1.xy / p1.w;
    vec2 delta_ndc = p1_ndc - p0_ndc;
    vec2 delta_px = delta_ndc * 0.5 * uScreen;
    float len_px = length(delta_px);
    vec2 perp_px = len_px > 1e-5 ? normalize(vec2(-delta_px.y, delta_px.x)) : vec2(1.0, 0.0);
    vec2 offset_px = perp_px * (uLineThickness * 0.5);
    vec2 offset_ndc = (offset_px * 2.0) / uScreen;

    vec4 o0 = offset_clip(p0, offset_ndc);
    vec4 o1 = offset_clip(p1, offset_ndc);

    gl_Position = p0 + o0;
    EmitVertex();
    gl_Position = p0 - o0;
    EmitVertex();
    gl_Position = p1 + o1;
    EmitVertex();
    gl_Position = p1 - o1;
    EmitVertex();
    EndPrimitive();
}
"""

TEXT_VERT_SHADER = """
#version 460 core
layout (location = 0) in vec2 aPos;
layout (location = 1) in vec2 aUV;
layout (location = 2) in vec3 iCenter;
layout (location = 3) in vec2 iOffset;
layout (location = 4) in vec2 iSize;
layout (location = 5) in vec4 iUV;
layout (location = 6) in vec3 iColor;

uniform mat4 uView;
uniform mat4 uProj;
uniform vec2 uScreen;
uniform float uLabelScale;
uniform float uDepthScale;
uniform float uDepthEnabled;

out vec2 vUV;
out vec3 vColor;

void main() {
    vec4 viewPos = uView * vec4(iCenter, 1.0);
    vec4 clip = uProj * viewPos;
    float depth = max(length(viewPos.xyz), 1e-6);
    float depthScale = uDepthScale / depth;
    float scale = mix(uLabelScale, depthScale, uDepthEnabled);
    vec2 pixel = (iOffset + aPos * iSize) * scale;
    vec2 ndcOffset = vec2((pixel.x / uScreen.x) * 2.0, -(pixel.y / uScreen.y) * 2.0);
    clip.xy += ndcOffset * clip.w;
    gl_Position = clip;
    vUV = iUV.xy + aUV * iUV.zw;
    vColor = iColor;
}
"""

TEXT_FRAG_SHADER = """
#version 460 core
in vec2 vUV;
in vec3 vColor;
out vec4 FragColor;

uniform sampler2D uAtlas;
uniform float uAlphaScale;

void main() {
    float alpha = texture(uAtlas, vUV).a * uAlphaScale;
    if (alpha <= 0.001) {
        discard;
    }
    FragColor = vec4(vColor, alpha);
}
"""

STRUCT_VERT_SHADER = """
#version 460 core
layout (location = 0) in vec2 aPos;
layout (location = 1) in vec3 iCenter;

uniform mat4 uView;
uniform mat4 uProj;
uniform vec2 uScreen;
uniform float uScale;
uniform float uDepthScale;
uniform float uDepthEnabled;

void main() {
    vec4 viewPos = uView * vec4(iCenter, 1.0);
    vec4 clip = uProj * viewPos;
    float depth = max(length(viewPos.xyz), 1e-6);
    float depthScale = uDepthScale / depth;
    float scale = mix(uScale, depthScale, uDepthEnabled);
    vec2 pixel = aPos * scale;
    vec2 ndcOffset = vec2((pixel.x / uScreen.x) * 2.0, -(pixel.y / uScreen.y) * 2.0);
    clip.xy += ndcOffset * clip.w;
    gl_Position = clip;
}
"""

STRUCT_FRAG_SHADER = """
#version 460 core
out vec4 FragColor;

uniform vec3 uColor;

void main() {
    FragColor = vec4(uColor, 1.0);
}
"""

SYSTEM_VERT_SHADER = """
#version 460 core
layout (location = 0) in vec2 aPos;

struct SystemData {
    vec4 pos_intel;
    vec4 intel_flags;
    vec4 flags_margin;
    vec4 honey_color;
    float has_ice_belt;
    float hasIncursionBoss;
    float has_upwell_cyno_jammer;
    float has_upwell_cyno_beacon;
};

layout(std430, binding = 2) readonly buffer Systems {
    SystemData systems[];
};

uniform mat4 uView;
uniform mat4 uProj;
uniform vec2 uScreen;
uniform vec2 uSize;
uniform float uScale;
uniform float uDepthScale;
uniform float uDepthEnabled;
uniform float uBorderThickness;
uniform float uOuterBorderThickness;
uniform float uAAMargin;
uniform float uHaloRadiusFactor;

out vec2 vLocal;
flat out vec2 vIntel;
flat out vec4 vFlagsA;
flat out float vFlagIncursion;
flat out float vFlagKill;
flat out vec4 vHoneyColor;
flat out float vHoneyMargin;
flat out float vScale;
flat out float vHasIceBelt;

void main() {
    SystemData sys = systems[gl_InstanceID];
    vec3 center = sys.pos_intel.xyz;
    float intel_status = sys.pos_intel.w;
    float intel_time = sys.intel_flags.x;
    float mark = sys.intel_flags.y;
    float monitored = sys.intel_flags.z;
    float populated = sys.intel_flags.w;
    float contested = sys.flags_margin.x;
    float incursion = sys.flags_margin.y;
    float kill = sys.flags_margin.z;
    float honey_margin = sys.flags_margin.w;
    vec4 honey_color = sys.honey_color;
    vHasIceBelt = sys.has_ice_belt;
    
    vec4 viewPos = uView * vec4(center, 1.0);
    vec4 clip = uProj * viewPos;
    float depth = max(length(viewPos.xyz), 1e-6);
    float depthScale = uDepthScale / depth;
    float scale = mix(uScale, depthScale, uDepthEnabled);
    vScale = scale;

    float scaledBorder = uBorderThickness * scale;
    float scaledOuter = uOuterBorderThickness * scale;
    float outer_gap = scaledBorder * 3.0;
    float padding = outer_gap + (scaledOuter * 2.0) + uAAMargin * scale;
    vec2 rect_half = 0.5 * uSize * scale;
    vec2 rect_extents = rect_half + vec2(padding);

    float halo_inner = max(uSize.x, uSize.y) * 0.5 * scale;
    float halo_outer = halo_inner * uHaloRadiusFactor;
    vec2 halo_extents = vec2(halo_outer);

    vec2 honey_padded = (uSize * scale) + vec2(honey_margin * scale * 2.0);
    vec2 honey_extents = honey_padded * 0.5;

    vec2 extents = max(rect_extents, max(halo_extents, honey_extents));

    vec2 pixel = (aPos - vec2(0.5)) * (extents * 2.0);
    vec2 ndcOffset = vec2((pixel.x / uScreen.x) * 2.0, -(pixel.y / uScreen.y) * 2.0);
    clip.xy += ndcOffset * clip.w;
    gl_Position = clip;

    vLocal = pixel;
    vIntel = vec2(intel_status, intel_time);
    vFlagsA = vec4(mark, monitored, populated, contested);
    vFlagIncursion = incursion;
    vFlagKill = kill;
    vHoneyColor = honey_color;
    vHoneyMargin = honey_margin;
}
"""

SYSTEM_FRAG_SHADER = """
#version 460 core
in vec2 vLocal;
flat in vec2 vIntel;
flat in vec4 vFlagsA;
flat in float vFlagIncursion;
flat in float vFlagKill;
flat in vec4 vHoneyColor;
flat in float vHoneyMargin;
flat in float vScale;
flat in float vHasIceBelt;

out vec4 FragColor;

uniform vec2 uSize;
uniform float uRadius;
uniform float uBorderThickness;
uniform float uOuterBorderThickness;
uniform float uAAMargin;
uniform vec4 uFillColor;
uniform vec4 uIntelColorGreen;
uniform vec4 uIntelColorRed;
uniform vec4 uBorderColor;
uniform vec4 uOuterBorderColor;
uniform float uIntelNow;
uniform float uIntelDuration;
uniform float uHaloRadiusFactor;
uniform vec4 uHaloColorMarked;
uniform vec4 uHaloColorKill;
uniform vec4 uHaloColorMonitored;
uniform vec4 uHaloColorPopulated;
uniform vec4 uHaloColorContested;
uniform vec4 uHaloColorIncursion;
uniform int uPass;

float roundedRectSdf(vec2 p, vec2 b, float r) {
    vec2 q = abs(p) - b + vec2(r);
    return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;
}

vec4 over(vec4 dst, vec4 src) {
    float outA = src.a + dst.a * (1.0 - src.a);
    if (outA <= 1e-6) {
        return vec4(0.0);
    }
    vec3 outRGB = (src.rgb * src.a + dst.rgb * dst.a * (1.0 - src.a)) / outA;
    return vec4(outRGB, outA);
}

vec4 clampColor(vec4 src, float a) {
    a = clamp(src.a*a, 0.0, 1.0);
    return vec4(src.rgb*a,a);
}

float octagonSdf(vec2 p, float rx, float ry ,float chamfer) {
      p = abs(p) - vec2(rx,ry);
      p = (p.y>p.x) ? p.yx : p.xy;
      p.y += chamfer*rx;
      const float k = 1.0-sqrt(2.0);
      if ( p.y<0.0 && p.y+p.x*k<0.0 )  return p.x;
      if( p.x<p.y ) return (p.x+p.y)*sqrt(0.5);    
      return length(p);
}

void main() {
    float scaledBorder = uBorderThickness * vScale;
    float scaledOuter = uOuterBorderThickness * vScale;
    float aa = uAAMargin * vScale;
    vec2 halfSize = 0.5 * uSize * vScale;
    float dist = roundedRectSdf(vLocal, halfSize, uRadius * vScale);
    float fill_alpha = 1.0 - smoothstep(0.0, 1.0, dist);
    float border_alpha = 1.0 - smoothstep(
        scaledBorder - 1.0, scaledBorder + 1.0, abs(dist)
    );
    float outer_gap = scaledBorder * 3.0;
    vec2 outerSize = halfSize + vec2(outer_gap + scaledOuter);
    float outerRadius = uRadius * vScale + outer_gap + scaledOuter;
    float outerDist = roundedRectSdf(vLocal, outerSize, outerRadius);
    float outer_alpha = 1.0 - smoothstep(
        scaledOuter - aa, scaledOuter + aa, abs(outerDist)
    );

    vec4 fillColor = uFillColor;
    float intelStatus = vIntel.x;
    float intelTime = vIntel.y;
    if (intelStatus > 0.0 && intelTime > 0.0 ) {
        vec4 intelColor = (intelStatus > 1.5) ? uIntelColorRed : uIntelColorGreen;
        fillColor = mix(uFillColor, intelColor, intelTime);
    }
    vec4 fill = vec4(fillColor.rgb, fillColor.a * fill_alpha);
    vec4 border = vec4(uBorderColor.rgb, uBorderColor.a * border_alpha);
    vec4 outer = vec4(uOuterBorderColor.rgb, uOuterBorderColor.a * outer_alpha*vHasIceBelt);
    vec4 innerMix = mix(fill, border, border_alpha);
    vec4 rect = mix(innerMix, outer, outer_alpha);

    float dist_h = length(vLocal);
    float inner = max(uSize.x, uSize.y) * 0.5 * vScale;
    float outer_h = inner * uHaloRadiusFactor;
    float halo_alpha = smoothstep( outer_h , inner, dist_h);
    vec4 base = vec4(0.0);
    base = over(base,clampColor(uHaloColorKill, vFlagKill));
    base = over(base,clampColor(uHaloColorMonitored, vFlagsA.y));
    base = over(base,clampColor(uHaloColorContested, vFlagsA.w));
    base = over(base,clampColor(uHaloColorIncursion, vFlagIncursion));
    base = over(base,clampColor(uHaloColorPopulated, vFlagsA.z));
    base = over(base,clampColor(uHaloColorMarked, vFlagsA.x));

    vec4 halo = vec4(base.rgb, base.a * halo_alpha);
    if (halo_alpha <= 0.0) {
        halo = vec4(0.0);
    }

    vec2 padded = (uSize * vScale) + vec2(vHoneyMargin * vScale * 2.0);
    float radius = padded.x * 0.48;
    float scaleY = (radius > 0.0) ? (padded.y / (1.80 * radius)) : 0.8;
    vec2 honey_local = vec2(vLocal.x, vLocal.y);
    float r1 = octagonSdf(honey_local, radius*0.9,radius*0.45,0.30);
    float honey_alpha = clamp(vHoneyColor.a, 0.0, 1.0);
    
    if ( r1 < 0.0 ){
        honey_alpha *= 1.0;
    }
    else{ 
        honey_alpha *= 0.0;
    }
    if (honey_alpha <= 0.001) {
        honey_alpha = 0.0;
    }
    vec4 honey = vec4(vHoneyColor.rgb, honey_alpha);

    vec4 color = vec4(0.0);
    if (uPass == 0) {
        color = halo;
    } else {
        color = over(color, honey);
        color = over(color, rect);
    }
    if (color.a <= 0.001) {
        discard;
    }
    FragColor = color;
}
"""

PICK_COMPUTE_SHADER = """
#version 460 core
layout (local_size_x = 256) in;

layout(std430, binding = 0) readonly buffer Positions {
    vec4 pos[];
};

layout(std430, binding = 1) writeonly buffer Distances {
    float dist[];
};

uniform mat4 uView;
uniform mat4 uProj;
uniform vec2 uScreen;
uniform vec2 uMouse;
uniform vec2 uHalfLabelBase;
uniform float uLabelScale;
uniform float uDepthScale;
uniform float uDepthEnabled;
uniform int uCount;
uniform int uMode; // 0 = 2D (stable ordering), 1 = 3D (depth)

void main() {
    uint idx = gl_GlobalInvocationID.x;
    if (idx >= uint(uCount)) {
        return;
    }
    vec4 world = pos[idx];
    vec4 viewPos = uView * vec4(world.xyz, 1.0);
    float depth = max(length(viewPos.xyz), 1e-6);
    float depthScale = uDepthScale / depth;
    float scale = mix(uLabelScale, depthScale, uDepthEnabled);
    vec2 halfLabel = uHalfLabelBase * scale;
    vec4 clip = uProj * viewPos;
    float w = clip.w;
    if (abs(w) <= 1e-6) {
        dist[idx] = 3.402823e38;
        return;
    }
    vec3 ndc = clip.xyz / w;
    if (abs(ndc.x) > 1.1 || abs(ndc.y) > 1.1 || ndc.z < -1.1 || ndc.z > 1.1) {
        dist[idx] = 3.402823e38;
        return;
    }
    float screen_x = (ndc.x * 0.5 + 0.5) * uScreen.x;
    float screen_y = (1.0 - (ndc.y * 0.5 + 0.5)) * uScreen.y;
    if (abs(screen_x - uMouse.x) > halfLabel.x || abs(screen_y - uMouse.y) > halfLabel.y) {
        dist[idx] = 3.402823e38;
        return;
    }
    if (uMode == 0) {
        dist[idx] = float(idx);
    } else {
        dist[idx] = length(viewPos.xyz);
    }
}
"""


def compile_shader(source: str, shader_type: int) -> int:
    """Compile a GLSL shader and return its OpenGL handle.

    Args:
        source: GLSL source code.
        shader_type: OpenGL shader type constant.

    Returns:
        The compiled shader handle.

    Raises:
        RuntimeError: If compilation fails.
    """
    shader = glCreateShader(shader_type)
    glShaderSource(shader, source)
    glCompileShader(shader)
    status = glGetShaderiv(shader, GL_COMPILE_STATUS)
    if not status:
        info = glGetShaderInfoLog(shader).decode("utf-8", "replace")
        glDeleteShader(shader)
        raise RuntimeError(f"Shader compile failed: {info}")
    return shader


def build_program(
    vertex_source: str, fragment_source: str, geometry_source: Optional[str] = None
) -> int:
    """Link a shader program from vertex/fragment sources, optional geometry shader.

    Args:
        vertex_source: GLSL vertex shader code.
        fragment_source: GLSL fragment shader code.
        geometry_source: Optional GLSL geometry shader code.

    Returns:
        The linked program handle.

    Raises:
        RuntimeError: If linking fails.
    """
    vert = compile_shader(vertex_source, GL_VERTEX_SHADER)
    frag = compile_shader(fragment_source, GL_FRAGMENT_SHADER)
    geom = compile_shader(geometry_source, GL_GEOMETRY_SHADER) if geometry_source else None
    program = glCreateProgram()
    glAttachShader(program, vert)
    glAttachShader(program, frag)
    if geom:
        glAttachShader(program, geom)
    glLinkProgram(program)
    status = glGetProgramiv(program, GL_LINK_STATUS)
    glDeleteShader(vert)
    glDeleteShader(frag)
    if geom:
        glDeleteShader(geom)
    if not status:
        info = glGetProgramInfoLog(program).decode("utf-8", "replace")
        glDeleteProgram(program)
        raise RuntimeError(f"Program link failed: {info}")
    return program


def build_compute_program(source: str) -> int:
    """Link a shader program from a compute shader source.

    Args:
        source: GLSL compute shader source code.

    Returns:
        Linked OpenGL program handle.

    Raises:
        RuntimeError: If program linking fails.
    """
    comp = compile_shader(source, GL_COMPUTE_SHADER)
    program = glCreateProgram()
    glAttachShader(program, comp)
    glLinkProgram(program)
    status = glGetProgramiv(program, GL_LINK_STATUS)
    glDeleteShader(comp)
    if not status:
        info = glGetProgramInfoLog(program).decode("utf-8", "replace")
        glDeleteProgram(program)
        raise RuntimeError(f"Compute program link failed: {info}")
    return program


def systems_to_array(systems: Iterable[System]) -> np.ndarray:
    """Convert system positions into a packed float array for GPU upload.

    Args:
        systems: Systems to convert.

    Returns:
        Float32 array shaped as (N, 3).
    """
    data = np.array([[s.x, s.y, s.z] for s in systems], dtype=np.float32)
    return data


def collect_name_chars(systems: Iterable[System]) -> List[str]:
    """Collect all unique characters from system names.

    Args:
        systems: Systems to scan for label characters.

    Returns:
        Sorted list of unique characters.
    """
    chars = set(string.printable)
    for sys in systems:
        for ch in sys.name_en:
            chars.add(ch)
    return sorted(chars)


def ortho(left: float, right: float, bottom: float, top: float, near: float, far: float) -> np.ndarray:
    """Create an orthographic projection matrix.

    Args:
        left: Left plane.
        right: Right plane.
        bottom: Bottom plane.
        top: Top plane.
        near: Near plane.
        far: Far plane.

    Returns:
        4x4 projection matrix.
    """
    mat = np.eye(4, dtype=np.float32)
    mat[0, 0] = 2.0 / (right - left)
    mat[1, 1] = 2.0 / (top - bottom)
    mat[2, 2] = -2.0 / (far - near)
    mat[0, 3] = -(right + left) / (right - left)
    mat[1, 3] = -(top + bottom) / (top - bottom)
    mat[2, 3] = -(far + near) / (far - near)
    return mat


def perspective(fov_y: float, aspect: float, near: float=0.01, far: float=100) -> np.ndarray:
    """Create a perspective projection matrix.

    Args:
        fov_y: Vertical field-of-view in radians.
        aspect: Viewport aspect ratio (width / height).
        near: Near clip plane distance.
        far: Far clip plane distance.

    Returns:
        4x4 projection matrix.
    """
    f = 1.0 / math.tan(fov_y * 0.5)
    mat = np.zeros((4, 4), dtype=np.float32)
    mat[0, 0] = f / max(aspect, 1e-6)
    mat[1, 1] = f
    mat[2, 2] = (far + near) / (near - far)
    mat[2, 3] = (2.0 * far * near) / (near - far)
    mat[3, 2] = -1.0
    return mat.T  # transpose so the layout matches OpenGL's column-major expectation


def look_at(eye: np.ndarray, target: np.ndarray, up: np.ndarray) -> np.ndarray:
    """Create a view matrix looking from eye to target.

    Args:
        eye: Camera eye position.
        target: Look-at target position.
        up: Up direction vector.

    Returns:
        4x4 view matrix.
    """
    forward = target - eye
    forward /= max(np.linalg.norm(forward), 1e-6)
    right = np.cross(forward, up)
    right /= max(np.linalg.norm(right), 1e-6)
    up_vec = np.cross(right, forward)

    mat = np.eye(4, dtype=np.float32)
    mat[0, 0:3] = right
    mat[1, 0:3] = up_vec
    mat[2, 0:3] = -forward
    mat[0, 3] = -np.dot(right, eye)
    mat[1, 3] = -np.dot(up_vec, eye)
    mat[2, 3] = np.dot(forward, eye)
    return mat.T  # transpose for column-major ordering in GL


def create_default_systems(count: int = 2000) -> List[System]:
    """Generate a random fallback system set for testing.

    Args:
        count: Number of systems to generate.

    Returns:
        List of generated systems.
    """
    rng = np.random.default_rng(7)
    positions = rng.normal(size=(count, 3)).astype(np.float32)
    positions *= rng.uniform(2.0, 10.0, size=(count, 1)).astype(np.float32)
    colors = rng.uniform(0.14, 0.26, size=(count, 3)).astype(np.float32)
    alphas = rng.uniform(0.6, 1.0, size=(count,)).astype(np.float32)
    margins = rng.uniform(6.0, 12.0, size=(count,)).astype(np.float32)
    return [
        System(
            float(x),
            float(y),
            float(z),
            f"System {i + 1}",
            "A",
            "B",
            "C",
            "D",
            0,
            0,
            IntelStatus.NONE,
            0.0,
            0,
            0,
            0,
            0,
            0,
            i,
            {},
            (float(color[0]), float(color[1]), float(color[2]), float(alpha)),
            float(margin),
        )
        for i, ((x, y, z), color, alpha, margin) in enumerate(
            zip(positions, colors, alphas, margins)
        )
    ]


def format_status(record: dict) -> str:
    """Create a short status string for a system.

    Args:
        record: Raw system record containing security data.

    Returns:
        Short formatted status string.
    """
    sec = record.get("securityStatus")
    if sec is None:
        return ""
    band = "High" if sec >= 0.45 else "Low" if sec >= 0.05 else "Null"
    return f"{band} {sec:.1f}"

def _parse_color_rgba(
    value: str, fallback: Tuple[float, float, float, float]
) -> Tuple[float, float, float, float]:
    """Convert a CSS color string to an RGBA tuple with a safe fallback.

    Args:
        value: CSS-like color string or alpha value.
        fallback: Fallback RGBA values if parsing fails.

    Returns:
        Parsed RGBA tuple.
    """
    raw = value.strip()
    if raw:
        try:
            alpha = float(raw)
            if math.isfinite(alpha):
                return (fallback[0], fallback[1], fallback[2], max(0.0, min(1.0, alpha)))
        except (TypeError, ValueError):
            pass
    color = QtGui.QColor(raw)
    if not color.isValid():
        return fallback
    r, g, b, a = color.getRgbF()
    return float(r), float(g), float(b), float(a)


def load_info_objects(path: str) -> dict:
    """Parse InfoObjects CSV into a lookup keyed by system name.

    Args:
        path: Path to the InfoObjects CSV.

    Returns:
        Mapping of system names to marker overrides.
    """
    markers: dict[str, dict] = {}
    if not path or not os.path.exists(path):
        return markers
    with open(path, "r", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if not row:
                continue
            first = row[0].strip() if row[0] else ""
            if first.startswith("#"):
                continue
            if len(row) < 5:
                continue
            region_name, marker_type, system_name, margin_str, color_str = [part.strip() for part in row[:5]]
            if not system_name:
                continue
            try:
                margin = float(margin_str)
            except (TypeError, ValueError):
                margin = 8.0
            color = _parse_color_rgba(color_str or "", (0.16, 0.2, 0.23, 1.0))
            marker_upper = marker_type.upper() if marker_type else ""
            markers[system_name] = {
                "region": region_name,
                "marker_type": marker_upper,
                "margin": margin,
                "color": color,
                "structure": 1 if marker_upper else 0,
            }
    return markers


def load_systems(
    path: str,
    target_radius: float = 20.0,
    info_objects_path: Optional[str] = None,
    mouse_3d=False
) -> List[System]:
    """Load systems from a JSONL file and normalize positions.

    Args:
        path: Path to the JSONL file.
        target_radius: Radius used to scale positions.
        info_objects_path: Optional CSV used to override per-system markers, margins, and honeycomb colors.

    Returns:
        List of systems with normalized coordinates.
    """
    positions = []
    records = []
    info_objects: dict[str, dict] = {}
    inferred_info_path = info_objects_path or os.path.join(os.path.dirname(path), "InfoObjects.txt")
    if os.path.exists(inferred_info_path):
        try:
            info_objects = load_info_objects(inferred_info_path)
        except (OSError, csv.Error) as exc:
            print(f"Failed to load {inferred_info_path}: {exc}")

    def pick_honeycomb_margin(structure: int) -> float:
        """Increase the background margin slightly for larger structures.

        Args:
            structure: Structure size indicator.

        Returns:
            Additional margin in pixels.
        """
        base = 8.0
        return base + float(max(structure, 0)) * 1.5
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            system_id = int(record.get("_key", -1))
            if system_id > 31999999:
                continue
            pos = None
            if mouse_3d:
                pos = record.get("position")
            else:
                pos = record.get("position2D")

            if not pos:
                continue
            positions.append([pos.get("x",0), pos.get("y",0), pos.get("z",0)])
            records.append(record)

    if not positions:
        return []

    coords = np.array(positions, dtype=np.float32)
    center = coords.mean(axis=0)
    coords -= center
    max_dist = np.linalg.norm(coords, axis=1).max()
    scale = target_radius / max(max_dist, 1.0)
    coords *= scale
    systems = []
    for (x, y, z), record in zip(coords, records):
        name_en = record.get("name", {}).get("en", "Unknown")
        status = format_status(record)
        sec_state = record.get("securityClass", "") or ""
        statistics = "stat"
        timer = "timer"
        marked = 15000 if name_en == "Ronne" else 0
        killed = 0
        intel_status = IntelStatus.NONE
        intel_status_time = 0.0
        monitored = 1 if name_en == "Anka" else 0
        populated = 1 if name_en == "Lamaa" else 0
        contested = 1 if name_en == "Iesa" else 0
        incursion = 1 if name_en == "Gammel" else 0
        structure = 0
        if name_en == "Iesa":
            structure = 1
        elif name_en == "Anka":
            structure = 2
        elif name_en == "Saikamon":
            structure = 3
        info = info_objects.get(name_en)
        if info:
            region_name = info.get("region")
            if region_name and not record.get("regionName"):
                record = dict(record)
                record["regionName"] = region_name
            structure = info.get("structure", structure) or structure

        system_id = int(record.get("_key", -1))
        honeycomb_color = (0.,0.,0.,0.)
        honeycomb_margin = pick_honeycomb_margin(structure)
        if info:
            honeycomb_color = info.get("color", honeycomb_color) or honeycomb_color
            honeycomb_margin = float(info.get("margin", honeycomb_margin))
        systems.append(
            System(
                float(x),
                float(y),
                float(z),
                name_en,
                status,
                sec_state,
                statistics,
                timer,
                marked,
                killed,
                intel_status,
                intel_status_time,
                monitored,
                populated,
                contested,
                incursion,
                structure,
                system_id,
                record,
                honeycomb_color,
                honeycomb_margin,
            )
        )
    return systems


def load_connections(
    path: str,
    systems: List[System],
    *,
    grouped: bool = False,
) -> np.ndarray | ConnectionLineGroups:
    """Load stargate connections into a flat vertex array.

    Args:
        path: Path to the stargates JSONL file.
        systems: Systems to match IDs against.
        grouped: If True, returns vertices split into groups based on whether
            the connection crosses constellations/regions.

    Returns:
        Either a float32 array of line vertices (x, y, z pairs), or a
        ConnectionLineGroups instance when ``grouped`` is True.
    """
    systems_by_id = {sys.system_id: sys for sys in systems if sys.system_id >= 0}
    pairs = set()
    verts: List[float] = []
    standard: List[float] = []
    cross_constellation: List[float] = []
    cross_region: List[float] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            src = record.get("solarSystemID")
            dst = record.get("destination", {}).get("solarSystemID")
            if src is None or dst is None:
                continue
            if src > 31999999 or dst > 31999999:
                continue
            if src not in systems_by_id or dst not in systems_by_id:
                continue
            key = (src, dst) if src < dst else (dst, src)
            if key in pairs:
                continue
            pairs.add(key)
            a = systems_by_id[src]
            b = systems_by_id[dst]
            if grouped:
                region_a = a.record.get("regionID")
                region_b = b.record.get("regionID")
                const_a = a.record.get("constellationID")
                const_b = b.record.get("constellationID")
                if region_a is not None and region_b is not None and region_a != region_b:
                    cross_region.extend([a.x, a.y, a.z, b.x, b.y, b.z])
                elif const_a is not None and const_b is not None and const_a != const_b:
                    cross_constellation.extend([a.x, a.y, a.z, b.x, b.y, b.z])
                else:
                    standard.extend([a.x, a.y, a.z, b.x, b.y, b.z])
            else:
                verts.extend([a.x, a.y, a.z, b.x, b.y, b.z])

    if grouped:
        return ConnectionLineGroups(
            np.array(standard, dtype=np.float32),
            np.array(cross_constellation, dtype=np.float32),
            np.array(cross_region, dtype=np.float32),
        )

    if not verts:
        return np.array([], dtype=np.float32)
    return np.array(verts, dtype=np.float32)


def load_jump_bridges(
    path: str,
    systems: List[System],
    segments: int = 16,
    bulge_factor: float = 0.16,
) -> np.ndarray:
    """Load jump-bridge style connections defined by system names.

    The file format is: ``<id> <source> --> <target>`` with ``#`` comments.
    Curves are emitted as a list of line segments approximating a quadratic
    Bezier with a gentle perpendicular bulge.

    Args:
        path: Path to the jump bridge file.
        systems: Systems to match names against.
        segments: Number of segments per curve.
        bulge_factor: Perpendicular bulge factor for the curve.

    Returns:
        Float32 array of line segment vertices.
    """
    systems_by_name = {sys.name_en: sys for sys in systems}
    verts: List[float] = []
    pairs = set()

    def bezier_segments(a: System, b: System) -> List[float]:
        """Build flat-ish quadratic Bezier segments between two systems.

        Args:
            a: Source system.
            b: Destination system.

        Returns:
            Flattened list of vertex pairs representing the curve.
        """
        ax, ay, az = a.x, a.y, a.z
        bx, by, bz = b.x, b.y, b.z
        dx = bx - ax
        dy = by - ay
        dist = math.hypot(dx, dy)
        if dist <= 1e-5:
            return []
        # Build a control point halfway along the edge, nudged perpendicular
        # to keep the curve nearly flat.
        px = -dy
        py = dx
        perp_len = math.hypot(px, py) or 1.0
        px /= perp_len
        py /= perp_len
        height = dist * bulge_factor
        cx = (ax + bx) * 0.5 + px * height
        cy = (ay + by) * 0.5 + py * height
        cz = (az + bz) * 0.5
        points: List[Tuple[float, float, float]] = []
        for i in range(segments + 1):
            t = i / float(segments)
            omt = 1.0 - t
            x = omt * omt * ax + 2.0 * omt * t * cx + t * t * bx
            y = omt * omt * ay + 2.0 * omt * t * cy + t * t * by
            z = omt * omt * az + 2.0 * omt * t * cz + t * t * bz
            points.append((x, y, z))
        segs: List[float] = []
        for i in range(len(points) - 1):
            x0, y0, z0 = points[i]
            x1, y1, z1 = points[i + 1]
            segs.extend([x0, y0, z0, x1, y1, z1])
        return segs

    pattern = re.compile(r"^\s*(\d+)\s+(.+?)\s+-->\s+(.+?)\s*$")
    with open(path, "r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            match = pattern.match(line)
            if not match:
                continue
            _, src_name, dst_name = match.groups()
            if src_name not in systems_by_name or dst_name not in systems_by_name:
                continue
            key = tuple(sorted((src_name, dst_name)))
            if key in pairs:
                continue
            pairs.add(key)
            a = systems_by_name[src_name]
            b = systems_by_name[dst_name]
            verts.extend(bezier_segments(a, b))

    if not verts:
        return np.array([], dtype=np.float32)
    return np.array(verts, dtype=np.float32)


STRUCTURE_GRIDS: dict[int, List[str]] = {
    1: [
        "  ******    ",
        "  ****+*    ",
        "  ******    ",
    ],
    2: [
        "   **     ",
        "   **     ",
        " ****+*   ",
        " ******   ",
    ],
    3: [
        " **  **   ",
        " **  **   ",
        " ****+*   ",
        " ******   ",
    ],
}


def _parse_structure_grid(
    lines: List[str],
) -> Tuple[
    List[Tuple[float, float, float, float]],
    int,
    int,
    set[Tuple[int, int]],
    int,
    int,
]:
    """Parse an ASCII structure template into border segments.

    The template uses `*` for filled cells and a single `+` to mark the anchor.
    Border segments are returned in grid-local coordinates relative to the `+`.

    Args:
        lines: ASCII rows of the template.

    Returns:
        A tuple containing:
            segments: List of (x0, y0, x1, y1) border segments.
            rows: Row count of the template.
            cols: Column count of the template.
            stars: Set of filled cell coordinates (row, col), including the `+` cell.
            plus_row: Row index of the `+` anchor.
            plus_col: Column index of the `+` anchor.
    """
    if not lines:
        return [], 0, 0, set(), 0, 0
    rows = len(lines)
    cols = max(len(line) for line in lines)
    padded = [line.ljust(cols) for line in lines]
    plus_row = plus_col = None
    stars: set[Tuple[int, int]] = set()
    for r, line in enumerate(padded):
        for c, ch in enumerate(line):
            if ch == "*":
                stars.add((r, c))
            if ch == "+":
                stars.add((r, c))
                plus_row, plus_col = r, c
    if plus_row is None:
        return [], rows, cols, stars, 0, 0

    def has_star(r: int, c: int) -> bool:
        """Return True if the grid cell is filled.

        Args:
            r: Row index.
            c: Column index.

        Returns:
            True if the cell is present in the filled-cell set.
        """
        return (r, c) in stars

    def pt(c: int, r: int) -> Tuple[float, float]:
        """Convert a grid cell coordinate to anchor-relative space.

        Args:
            c: Column index.
            r: Row index.

        Returns:
            (x, y) coordinates with (0, 0) at the `+` anchor.
        """
        x = (c - plus_col)
        # Invert Y so grid rows increase upward after projection
        y = (r - plus_row)
        return x, y

    segments: set[Tuple[Tuple[float, float], Tuple[float, float]]] = set()
    for r, c in stars:
        left = not has_star(r, c - 1)
        right = not has_star(r, c + 1)
        top = not has_star(r - 1, c)
        bottom = not has_star(r + 1, c)
        if left:
            segments.add((pt(c, r), pt(c, r + 1)))
        if right:
            segments.add((pt(c + 1, r), pt(c + 1, r + 1)))
        if top:
            segments.add((pt(c, r), pt(c + 1, r)))
        if bottom:
            segments.add((pt(c, r + 1), pt(c + 1, r + 1)))

    flat: List[Tuple[float, float, float, float]] = []
    for (x0, y0), (x1, y1) in sorted(segments, key=lambda s: (s[0][1], s[0][0], s[1][1], s[1][0])):
        flat.append((x0, y0, x1, y1))
    return flat, rows, cols, stars, plus_row, plus_col


STRUCTURE_TEMPLATES = {
    key: _parse_structure_grid(lines) for key, lines in STRUCTURE_GRIDS.items()
}


def generate_font_atlas(
    atlas_dir: str,
    font_family: str,
    font_size: int,
    chars: List[str],
    logical_font_size: Optional[int] = None,
) -> Tuple[str, str]:
    """Generate a bitmap font atlas with glyph metrics.

    Args:
        atlas_dir: Output directory for atlas files.
        font_family: Font family name.
        font_size: Font size in points.
        chars: Characters to include.
        logical_font_size: Optional logical size used for layout; if provided,
            metrics are scaled to this size while the atlas is rasterized at
            `font_size` for higher quality.

    Returns:
        Tuple of (image_path, json_path).
    """
    os.makedirs(atlas_dir, exist_ok=True)
    image_path = os.path.join(atlas_dir, "atlas.png")
    json_path = os.path.join(atlas_dir, "atlas.json")

    font = QtGui.QFont(font_family)
    font.setPointSize(font_size)
    font.setHintingPreference(QtGui.QFont.HintingPreference.PreferFullHinting)
    font.setStyleStrategy(QtGui.QFont.StyleStrategy.PreferAntialias)
    metrics = QtGui.QFontMetrics(font)
    logical_size = float(logical_font_size if logical_font_size is not None else font_size)
    logical_scale = logical_size / float(font_size) if font_size else 1.0

    padding = 2
    atlas_width = 1024
    x = padding
    y = padding
    row_height = 0
    glyphs = {}

    for ch in chars:
        rect = metrics.boundingRect(ch)
        width = rect.width()
        height = rect.height()
        box_w = width + padding * 2
        box_h = height + padding * 2
        if x + box_w > atlas_width:
            x = padding
            y += row_height + padding
            row_height = 0
        glyphs[ch] = {
            "x": x + padding,
            "y": y + padding,
            "w": width,
            "h": height,
            "bearing_x": rect.left(),
            "bearing_y": rect.top(),
            "advance": metrics.horizontalAdvance(ch),
        }
        x += box_w
        row_height = max(row_height, box_h)

    atlas_height = y + row_height + padding

    image = QtGui.QImage(atlas_width, atlas_height, QtGui.QImage.Format.Format_RGBA8888)
    image.fill(QtGui.QColor(0, 0, 0, 0))
    painter = QtGui.QPainter(image)
    painter.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing, True)
    painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)
    painter.setFont(font)
    painter.setPen(QtGui.QColor(255, 255, 255, 255))

    for ch, glyph in glyphs.items():
        if glyph["w"] <= 0 or glyph["h"] <= 0:
            continue
        baseline = QtCore.QPointF(
            glyph["x"] - glyph["bearing_x"], glyph["y"] - glyph["bearing_y"]
        )
        painter.drawText(baseline, ch)
    painter.end()
    image.save(image_path)

    payload = {
        "font_family": font_family,
        "font_size": font_size,
        "image": "atlas.png",
        "size": [atlas_width, atlas_height],
        "logical_scale": logical_scale,
        "metrics": {
            "height": metrics.height(),
            "ascent": metrics.ascent(),
            "descent": metrics.descent(),
        },
        "glyphs": glyphs,
    }
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)

    return image_path, json_path

def load_atlas(json_path: str) -> dict:
    """Load atlas metadata and resolve the atlas image path.

    Args:
        json_path: Path to the atlas JSON file.

    Returns:
        Atlas metadata dictionary.
    """
    with open(json_path, "r", encoding="utf-8") as handle:
        atlas = json.load(handle)
    image = atlas.get("image", "atlas.png")
    if not os.path.isabs(image):
        image = os.path.join(os.path.dirname(json_path), image)
    atlas["image"] = image
    return atlas


def select_font_family(preferred: List[str]) -> str:
    """Pick the first available font from a preference list.

    Args:
        preferred: Ordered list of font families to try.

    Returns:
        The selected font family name.
    """
    available = set(QtGui.QFontDatabase.families())
    for name in preferred:
        if name in available:
            return name
    return preferred[-1]


class StarMapWidget(QtOpenGLWidgets.QOpenGLWidget):
    """OpenGL widget that renders systems, connections, and labels.

    Emits `systemDoubleClicked` when the user double-clicks a system label.
    Emits `systemRightClicked` when the user right-clicks a system label.

    Attributes:
        systemDoubleClicked: Signal emitted on system double-click.
        systemRightClicked: Signal emitted on system right-click.
    """

    INTEL_FADE_SECONDS = 30.0
    TEXT_FADE_START_SCALE = 0.1
    TEXT_FADE_END_SCALE = 0.30

    def __init__(
        self,
        systems: dict[int,System],
        atlas_path: str,
        line_vertices: np.ndarray | ConnectionLineGroups,
        jump_bridge_vertices: Optional[np.ndarray] = None,
        line_thickness: float = 1.0,
        mouse_3d: bool = False,
        show_jumpbridges: bool = True,
        show_timers: bool =  True,
        show_statistic: bool =  True,
        parent=None,
    ) -> None:
        """Initialize the OpenGL widget and label data.

        Args:
            systems: Systems to render.
            atlas_path: Path to the font atlas JSON.
            line_vertices: Connection vertices (optionally grouped for multi-color rendering).
            jump_bridge_vertices: Optional curved jump-bridge vertices.
            line_thickness: Screen-space thickness in pixels for system connections.
            mouse_3d: If True, use orbit-style 3D mouse controls instead of flat panning.
            parent: Optional Qt parent widget.

        Returns:
            None.
        """
        super().__init__(parent)
        self.line_program = 0
        self.text_program = 0
        self.structure_program = 0
        self.system_program = 0
        self.pick_program = 0
        self.point_vao = 0
        self.point_vbo = 0
        self.line_vao = 0
        self.line_vbo = 0
        self.line_constellation_vao = 0
        self.line_constellation_vbo = 0
        self.line_region_vao = 0
        self.line_region_vbo = 0
        self.bridge_line_vao = 0
        self.bridge_line_vbo = 0
        self.text_vao = 0
        self.text_dynamic_vao = 0
        self.text_vbo = 0
        self.text_instance_vbo = 0
        self.text_dynamic_instance_vbo = 0
        self.text_instance_count = 0
        self.text_dynamic_instance_count = 0
        self.system_vao = 0
        self.system_ssbo = 0
        self.system_instance_count = 0
        self.pick_positions_ssbo = 0
        self.pick_distances_ssbo = 0
        self._pick_positions = np.array([], dtype=np.float32)
        self._gpu_picking_enabled = True
        self.structure_draws: List[dict] = []
        self.atlas_texture = 0
        self.atlas = load_atlas(atlas_path)
        self.systems = list(systems.values())
        now_utc = time.time()
        intel_times = [sys.intel_status_time for sys in self.systems if sys.intel_status_time > 0.0]
        self.intel_time_base = min([now_utc] + intel_times)
        self.intel_fade_seconds = float(self.INTEL_FADE_SECONDS)
        self.system_index_by_id = {sys.system_id: idx for idx, sys in enumerate(self.systems)}
        self._intel_status_active = False
        self._show_intel_minutes = False
        self._text_rebuild_pending = False
        self._text_dynamic_rebuild_pending = False
        self.atlas_scale = float(self.atlas.get("logical_scale", 1.0))
        self.font_scale = 1.4
        self.secondary_text_scale = 0.7
        self.mark_timers = {idx: max(0.0, float(sys.marker)) for idx, sys in enumerate(self.systems)}
        self.kill_timers = {idx: max(0.0, float(sys.hasKill)) for idx, sys in enumerate(self.systems)}
        self._system_rebuild_pending = False

        self.vertices = np.array([[s.x, s.y, s.z] for s in self.systems], dtype=np.float32)
        if self.vertices.size:
            self._pick_positions = np.zeros((self.vertices.shape[0], 4), dtype=np.float32)
            self._pick_positions[:, :3] = self.vertices
            self._pick_positions[:, 3] = 1.0
        self.system_instances = self._build_system_instances()
        self.system_instance_count = (
            self.system_instances.shape[0] if self.system_instances.size else 0
        )
        if isinstance(line_vertices, ConnectionLineGroups):
            self.line_vertices = line_vertices.standard
            self.line_vertices_cross_constellation = line_vertices.cross_constellation
            self.line_vertices_cross_region = line_vertices.cross_region
        else:
            self.line_vertices = line_vertices
            self.line_vertices_cross_constellation = np.array([], dtype=np.float32)
            self.line_vertices_cross_region = np.array([], dtype=np.float32)
        self.bridge_line_vertices = (
            jump_bridge_vertices if jump_bridge_vertices is not None else np.array([], dtype=np.float32)
        )
        self.line_thickness = max(0.1, float(line_thickness))
        self.mouse_3d = bool(mouse_3d)
        self.orbiting = False
        self.orbit_yaw = 0.0
        self.orbit_pitch = -0.45
        self.camera_distance = 60.0
        self.camera_target = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.u_line_view = -1
        self.u_line_proj = -1
        self.u_line_color = -1
        self.u_line_screen = -1
        self.u_line_thickness = -1
        self.u_struct_view = -1
        self.u_struct_proj = -1
        self.u_struct_screen = -1
        self.u_struct_scale = -1
        self.u_struct_color = -1
        self.u_struct_depth_scale = -1
        self.u_struct_depth_enabled = -1
        self.u_system_view = -1
        self.u_system_proj = -1
        self.u_system_screen = -1
        self.u_system_size = -1
        self.u_system_radius = -1
        self.u_system_scale = -1
        self.u_system_depth_scale = -1
        self.u_system_depth_enabled = -1
        self.u_system_border_thickness = -1
        self.u_system_outer_border_thickness = -1
        self.u_system_aa_margin = -1
        self.u_system_fill = -1
        self.u_system_intel_color_green = -1
        self.u_system_intel_color_red = -1
        self.u_system_border = -1
        self.u_system_outer_border = -1
        self.u_system_intel_now = -1
        self.u_system_intel_duration = -1
        self.u_system_halo_radius = -1
        self.u_system_pass = -1
        self.u_system_halo_color_marked = -1
        self.u_system_halo_color_kill = -1
        self.u_system_halo_color_monitored = -1
        self.u_system_halo_color_populated = -1
        self.u_system_halo_color_contested = -1
        self.u_system_halo_color_incursion = -1
        self.u_pick_view = -1
        self.u_pick_proj = -1
        self.u_pick_screen = -1
        self.u_pick_mouse = -1
        self.u_pick_half_label_base = -1
        self.u_pick_label_scale = -1
        self.u_pick_depth_scale = -1
        self.u_pick_depth_enabled = -1
        self.u_pick_count = -1
        self.u_pick_mode = -1
        self.u_screen = -1
        self.u_atlas = -1
        self.u_text_view = -1
        self.u_text_proj = -1
        self.u_text_scale = -1
        self.u_text_depth_scale = -1
        self.u_text_depth_enabled = -1
        self.u_text_alpha_scale = -1
        self.text_fade_start_scale = float(self.TEXT_FADE_START_SCALE)
        self.text_fade_end_scale = float(self.TEXT_FADE_END_SCALE)
        self.label_padding = 8.0
        self.label_line_gap = 3.0
        metrics = self.atlas.get("metrics", {})
        self.label_ascent = float(metrics.get("ascent", metrics.get("height", 9))) * self.atlas_scale
        self.label_descent = float(metrics.get("descent", 0.0)) * self.atlas_scale
        self.label_line_height = self.label_ascent + self.label_descent
        self.label_width, self.label_height = self._compute_label_size()
        self.label_radius = self.label_height / 2
        self.halo_radius_factor = 1.5
        self.rect_fill_color = (0.10, 0.12, 0.12, 1.0)
        self.intel_color_green = (0.2, 0.6, 0.2, 1.0)
        self.intel_color_red = (0.7, 0.2, 0.2, 1.0)
        self.halo_color_marked = (0.36, 0.76, 0.93, 1.0)      # light blue
        self.halo_color_kill = (1.0, 0.0, 0.0, 1.0)      # red
        self.halo_color_monitored = (1.0, 1.0, 1.0, 0.3)   # white
        self.halo_color_populated = (0.75, 0.55, 1.0, 1.0) # purple
        self.halo_color_contested = (0.75, 0.2, 0.2, 1.0)    # red
        self.halo_color_incursion = (1.0, 1.0, 0.0, 1.0)  # yellow
        self.structure_vertices = self._build_structure_vertices()
        self.structure_instances = self._build_structure_instances()
        self.target = np.array([0.0, 0.0], dtype=np.float32)
        self.base_span = 30.0
        self.zoom = 60.2
        self.base_zoom = self.zoom
        self.camera_distance = float(self.zoom)
        self.panning = False
        self.show_jumpbridges = show_jumpbridges
        self.show_timers = show_timers
        self.show_statistic  = show_statistic
        self.last_pos = QtCore.QPointF()
        self.text_instances, self.text_dynamic_instances = self._build_text_instances(time.time())
        self.text_instance_count = self.text_instances.shape[0] if self.text_instances.size else 0
        self.text_dynamic_instance_count =  self.text_dynamic_instances.shape[0] if self.text_dynamic_instances.size else 0
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self._hovered_system: Optional[System] = None
        self._last_mouse_pos: Optional[QtCore.QPointF] = None
        self._fps_smoothed = 0.0
        self._fps_alpha = 0.12
        self._hud_padding = 8
        self._hud_radius = 6
        self._hud_bg = QtGui.QColor(12, 14, 16, 80)
        self._hud_text = QtGui.QColor(235, 235, 235, 80)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(int(1000 / 25))
        self._last_frame_time = time.monotonic()
    systemDoubleClicked =  PySide6.QtCore.Signal(int)
    systemRightClicked = PySide6.QtCore.Signal(int)

    def updateJumpBridges(self,jump_bridge_vertices: Optional[np.ndarray]):
        self.bridge_line_vertices = (
            jump_bridge_vertices if jump_bridge_vertices is not None else np.array([], dtype=np.float32)
        )

    def initializeGL(self) -> None:
        """Initialize OpenGL programs, buffers, and textures.

        Returns:
            None.
        """
        glViewport(0, 0, self.width(), self.height())
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        glEnable(GL_PROGRAM_POINT_SIZE)
        glEnable(GL_MULTISAMPLE)
        glEnable(GL_LINE_SMOOTH)
        glDepthFunc(GL_LESS)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)

        self.line_program = build_program(LINE_VERT_SHADER, LINE_FRAG_SHADER, LINE_GEOM_SHADER)
        self.text_program = build_program(TEXT_VERT_SHADER, TEXT_FRAG_SHADER)
        self.structure_program = build_program(STRUCT_VERT_SHADER, STRUCT_FRAG_SHADER)
        self.system_program = build_program(SYSTEM_VERT_SHADER, SYSTEM_FRAG_SHADER)
        if self._gpu_picking_enabled and self._pick_positions.size:
            try:
                self.pick_program = build_compute_program(PICK_COMPUTE_SHADER)
                self.u_pick_view = glGetUniformLocation(self.pick_program, "uView")
                self.u_pick_proj = glGetUniformLocation(self.pick_program, "uProj")
                self.u_pick_screen = glGetUniformLocation(self.pick_program, "uScreen")
                self.u_pick_mouse = glGetUniformLocation(self.pick_program, "uMouse")
                self.u_pick_half_label_base = glGetUniformLocation(
                    self.pick_program, "uHalfLabelBase"
                )
                self.u_pick_label_scale = glGetUniformLocation(self.pick_program, "uLabelScale")
                self.u_pick_depth_scale = glGetUniformLocation(self.pick_program, "uDepthScale")
                self.u_pick_depth_enabled = glGetUniformLocation(
                    self.pick_program, "uDepthEnabled"
                )
                self.u_pick_count = glGetUniformLocation(self.pick_program, "uCount")
                self.u_pick_mode = glGetUniformLocation(self.pick_program, "uMode")
                self.pick_positions_ssbo = glGenBuffers(1)
                glBindBuffer(GL_SHADER_STORAGE_BUFFER, self.pick_positions_ssbo)
                glBufferData(
                    GL_SHADER_STORAGE_BUFFER,
                    self._pick_positions.nbytes,
                    self._pick_positions,
                    GL_STATIC_DRAW,
                )
                self.pick_distances_ssbo = glGenBuffers(1)
                glBindBuffer(GL_SHADER_STORAGE_BUFFER, self.pick_distances_ssbo)
                glBufferData(
                    GL_SHADER_STORAGE_BUFFER,
                    self._pick_positions.shape[0] * ctypes.sizeof(ctypes.c_float),
                    None,
                    GL_DYNAMIC_READ,
                )
            except RuntimeError as exc:
                self.pick_program = 0
                self._gpu_picking_enabled = False
                print(f"Failed to initialize GPU picking: {exc}")
        self.point_vao = glGenVertexArrays(1)
        self.point_vbo = glGenBuffers(1)
        glBindVertexArray(self.point_vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.point_vbo)
        glBufferData(GL_ARRAY_BUFFER, self.vertices.nbytes, self.vertices, GL_STATIC_DRAW)
        glVertexAttribPointer(
            0, 3, GL_FLOAT, False, 3 * ctypes.sizeof(ctypes.c_float), ctypes.c_void_p(0)
        )
        glEnableVertexAttribArray(0)

        self.u_line_view = glGetUniformLocation(self.line_program, "uView")
        self.u_line_proj = glGetUniformLocation(self.line_program, "uProj")
        self.u_line_color = glGetUniformLocation(self.line_program, "uColor")
        self.u_line_screen = glGetUniformLocation(self.line_program, "uScreen")
        self.u_line_thickness = glGetUniformLocation(self.line_program, "uLineThickness")
        self.u_struct_view = glGetUniformLocation(self.structure_program, "uView")
        self.u_struct_proj = glGetUniformLocation(self.structure_program, "uProj")
        self.u_struct_screen = glGetUniformLocation(self.structure_program, "uScreen")
        self.u_struct_scale = glGetUniformLocation(self.structure_program, "uScale")
        self.u_struct_color = glGetUniformLocation(self.structure_program, "uColor")
        self.u_struct_depth_scale = glGetUniformLocation(self.structure_program, "uDepthScale")
        self.u_struct_depth_enabled = glGetUniformLocation(self.structure_program, "uDepthEnabled")
        self.u_system_view = glGetUniformLocation(self.system_program, "uView")
        self.u_system_proj = glGetUniformLocation(self.system_program, "uProj")
        self.u_system_screen = glGetUniformLocation(self.system_program, "uScreen")
        self.u_system_size = glGetUniformLocation(self.system_program, "uSize")
        self.u_system_radius = glGetUniformLocation(self.system_program, "uRadius")
        self.u_system_scale = glGetUniformLocation(self.system_program, "uScale")
        self.u_system_depth_scale = glGetUniformLocation(self.system_program, "uDepthScale")
        self.u_system_depth_enabled = glGetUniformLocation(self.system_program, "uDepthEnabled")
        self.u_system_border_thickness = glGetUniformLocation(self.system_program, "uBorderThickness")
        self.u_system_outer_border_thickness = glGetUniformLocation(
            self.system_program, "uOuterBorderThickness"
        )
        self.u_system_aa_margin = glGetUniformLocation(self.system_program, "uAAMargin")
        self.u_system_fill = glGetUniformLocation(self.system_program, "uFillColor")
        self.u_system_intel_color_green = glGetUniformLocation(self.system_program, "uIntelColorGreen")
        self.u_system_intel_color_red = glGetUniformLocation(self.system_program, "uIntelColorRed")
        self.u_system_border = glGetUniformLocation(self.system_program, "uBorderColor")
        self.u_system_outer_border = glGetUniformLocation(self.system_program, "uOuterBorderColor")
        self.u_system_intel_now = glGetUniformLocation(self.system_program, "uIntelNow")
        self.u_system_intel_duration = glGetUniformLocation(self.system_program, "uIntelDuration")
        self.u_system_halo_radius = glGetUniformLocation(self.system_program, "uHaloRadiusFactor")
        self.u_system_pass = glGetUniformLocation(self.system_program, "uPass")
        self.u_system_halo_color_marked = glGetUniformLocation(
            self.system_program, "uHaloColorMarked"
        )
        self.u_system_halo_color_kill = glGetUniformLocation(self.system_program, "uHaloColorKill")
        self.u_system_halo_color_monitored = glGetUniformLocation(
            self.system_program, "uHaloColorMonitored"
        )
        self.u_system_halo_color_populated = glGetUniformLocation(
            self.system_program, "uHaloColorPopulated"
        )
        self.u_system_halo_color_contested = glGetUniformLocation(
            self.system_program, "uHaloColorContested"
        )
        self.u_system_halo_color_incursion = glGetUniformLocation(
            self.system_program, "uHaloColorIncursion"
        )

        if self.line_vertices.size:
            self.line_vao = glGenVertexArrays(1)
            self.line_vbo = glGenBuffers(1)
            glBindVertexArray(self.line_vao)
            glBindBuffer(GL_ARRAY_BUFFER, self.line_vbo)
            glBufferData(
                GL_ARRAY_BUFFER, self.line_vertices.nbytes, self.line_vertices, GL_STATIC_DRAW
            )
            glVertexAttribPointer(
                0, 3, GL_FLOAT, False, 3 * ctypes.sizeof(ctypes.c_float), ctypes.c_void_p(0)
            )
            glEnableVertexAttribArray(0)

        if True and self.line_vertices_cross_constellation.size:
            self.line_constellation_vao = glGenVertexArrays(1)
            self.line_constellation_vbo = glGenBuffers(1)
            glBindVertexArray(self.line_constellation_vao)
            glBindBuffer(GL_ARRAY_BUFFER, self.line_constellation_vbo)
            glBufferData(
                GL_ARRAY_BUFFER,
                self.line_vertices_cross_constellation.nbytes,
                self.line_vertices_cross_constellation,
                GL_STATIC_DRAW,
            )
            glVertexAttribPointer(
                0, 3, GL_FLOAT, False, 3 * ctypes.sizeof(ctypes.c_float), ctypes.c_void_p(0)
            )
            glEnableVertexAttribArray(0)

        if True and self.line_vertices_cross_region.size:
            self.line_region_vao = glGenVertexArrays(1)
            self.line_region_vbo = glGenBuffers(1)
            glBindVertexArray(self.line_region_vao)
            glBindBuffer(GL_ARRAY_BUFFER, self.line_region_vbo)
            glBufferData(
                GL_ARRAY_BUFFER,
                self.line_vertices_cross_region.nbytes,
                self.line_vertices_cross_region,
                GL_STATIC_DRAW,
            )
            glVertexAttribPointer(
                0, 3, GL_FLOAT, False, 3 * ctypes.sizeof(ctypes.c_float), ctypes.c_void_p(0)
            )
            glEnableVertexAttribArray(0)

        if True and self.bridge_line_vertices.size:
            self.bridge_line_vao = glGenVertexArrays(1)
            self.bridge_line_vbo = glGenBuffers(1)
            glBindVertexArray(self.bridge_line_vao)
            glBindBuffer(GL_ARRAY_BUFFER, self.bridge_line_vbo)
            glBufferData(
                GL_ARRAY_BUFFER,
                self.bridge_line_vertices.nbytes,
                self.bridge_line_vertices,
                GL_STATIC_DRAW,
            )
            glVertexAttribPointer(
                0, 3, GL_FLOAT, False, 3 * ctypes.sizeof(ctypes.c_float), ctypes.c_void_p(0)
            )
            glEnableVertexAttribArray(0)

        self.text_vao = glGenVertexArrays(1)
        self.text_dynamic_vao = glGenVertexArrays(1)
        self.text_vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.text_vbo)
        quad = np.array(
            [
                0.0,
                0.0,
                0.0,
                0.0,
                1.0,
                0.0,
                1.0,
                0.0,
                0.0,
                1.0,
                0.0,
                1.0,
                1.0,
                1.0,
                1.0,
                1.0,
            ],
            dtype=np.float32,
        )
        glBufferData(GL_ARRAY_BUFFER, quad.nbytes, quad, GL_STATIC_DRAW)
        for vao in (self.text_vao, self.text_dynamic_vao):
            glBindVertexArray(vao)
            glBindBuffer(GL_ARRAY_BUFFER, self.text_vbo)
            glVertexAttribPointer(
                0, 2, GL_FLOAT, False, 4 * ctypes.sizeof(ctypes.c_float), ctypes.c_void_p(0)
            )
            glEnableVertexAttribArray(0)
            glVertexAttribPointer(
                1,
                2,
                GL_FLOAT,
                False,
                4 * ctypes.sizeof(ctypes.c_float),
                ctypes.c_void_p(2 * ctypes.sizeof(ctypes.c_float)),
            )
            glEnableVertexAttribArray(1)

        self.system_vao = glGenVertexArrays(1)
        glBindVertexArray(self.system_vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.text_vbo)
        glVertexAttribPointer(
            0, 2, GL_FLOAT, False, 4 * ctypes.sizeof(ctypes.c_float), ctypes.c_void_p(0)
        )
        glEnableVertexAttribArray(0)

        self.system_ssbo = glGenBuffers(1)
        glBindBuffer(GL_SHADER_STORAGE_BUFFER, self.system_ssbo)
        if self.system_instances.size:
            system_data = self.system_instances
            system_size = self.system_instances.nbytes
        else:
            system_data = None
            system_size = 0
        glBufferData(GL_SHADER_STORAGE_BUFFER, system_size, system_data, GL_DYNAMIC_DRAW)

        if True and self.structure_program:
            for key, parts in self.structure_vertices.items():
                centers = self.structure_instances.get(key, np.array([], dtype=np.float32))
                if centers.size == 0:
                    continue
                draw_entry = {
                    "fill_vao": 0,
                    "fill_vbo": 0,
                    "border_vao": 0,
                    "border_vbo": 0,
                    "inst_vbo": 0,
                    "fill_count": 0,
                    "border_count": 0,
                    "instance_count": centers.shape[0],
                }
                glBindVertexArray(0)
                if parts.get("fill") is not None and parts["fill"].size:
                    draw_entry["fill_vao"] = glGenVertexArrays(1)
                    draw_entry["fill_vbo"] = glGenBuffers(1)
                    glBindVertexArray(draw_entry["fill_vao"])
                    glBindBuffer(GL_ARRAY_BUFFER, draw_entry["fill_vbo"])
                    glBufferData(GL_ARRAY_BUFFER, parts["fill"].nbytes, parts["fill"], GL_STATIC_DRAW)
                    glVertexAttribPointer(
                        0, 2, GL_FLOAT, False, 2 * ctypes.sizeof(ctypes.c_float), ctypes.c_void_p(0)
                    )
                    glEnableVertexAttribArray(0)
                    draw_entry["fill_count"] = parts["fill"].size // 2
                if parts.get("border") is not None and parts["border"].size:
                    draw_entry["border_vao"] = glGenVertexArrays(1)
                    draw_entry["border_vbo"] = glGenBuffers(1)
                    glBindVertexArray(draw_entry["border_vao"])
                    glBindBuffer(GL_ARRAY_BUFFER, draw_entry["border_vbo"])
                    glBufferData(GL_ARRAY_BUFFER, parts["border"].nbytes, parts["border"], GL_STATIC_DRAW)
                    glVertexAttribPointer(
                        0, 2, GL_FLOAT, False, 2 * ctypes.sizeof(ctypes.c_float), ctypes.c_void_p(0)
                    )
                    glEnableVertexAttribArray(0)
                    draw_entry["border_count"] = parts["border"].size // 2
                draw_entry["inst_vbo"] = glGenBuffers(1)
                glBindVertexArray(draw_entry["fill_vao"] or draw_entry["border_vao"])
                glBindBuffer(GL_ARRAY_BUFFER, draw_entry["inst_vbo"])
                glBufferData(GL_ARRAY_BUFFER, centers.nbytes, centers, GL_STATIC_DRAW)
                def bind_instance_attrib(vao: int) -> None:
                    """Bind the per-instance center attribute to a VAO.

                    Args:
                        vao: Vertex array object to update.

                    Returns:
                        None.
                    """
                    glBindVertexArray(vao)
                    glBindBuffer(GL_ARRAY_BUFFER, draw_entry["inst_vbo"])
                    glVertexAttribPointer(
                        1, 3, GL_FLOAT, False, 3 * ctypes.sizeof(ctypes.c_float), ctypes.c_void_p(0)
                    )
                    glEnableVertexAttribArray(1)
                    glVertexAttribDivisor(1, 1)

                if draw_entry["fill_vao"]:
                    bind_instance_attrib(draw_entry["fill_vao"])
                if draw_entry["border_vao"]:
                    bind_instance_attrib(draw_entry["border_vao"])
                self.structure_draws.append(draw_entry)

        self.u_screen = glGetUniformLocation(self.text_program, "uScreen")
        self.u_atlas = glGetUniformLocation(self.text_program, "uAtlas")
        self.u_text_view = glGetUniformLocation(self.text_program, "uView")
        self.u_text_proj = glGetUniformLocation(self.text_program, "uProj")
        self.u_text_scale = glGetUniformLocation(self.text_program, "uLabelScale")
        self.u_text_depth_scale = glGetUniformLocation(self.text_program, "uDepthScale")
        self.u_text_depth_enabled = glGetUniformLocation(self.text_program, "uDepthEnabled")
        self.u_text_alpha_scale = glGetUniformLocation(self.text_program, "uAlphaScale")

        def bind_text_instances(vao: int, vbo: int, instances: np.ndarray) -> None:
            """Bind per-instance glyph attributes to a text VAO.

            Args:
                vao: Vertex array object to update.
                vbo: Instance buffer object to upload.
                instances: Instance data to bind.

            Returns:
                None.
            """
            glBindVertexArray(vao)
            glBindBuffer(GL_ARRAY_BUFFER, vbo)
            glBufferData(GL_ARRAY_BUFFER, instances.nbytes, instances, GL_DYNAMIC_DRAW)
            stride = 14 * ctypes.sizeof(ctypes.c_float)
            glVertexAttribPointer(2, 3, GL_FLOAT, False, stride, ctypes.c_void_p(0))
            glEnableVertexAttribArray(2)
            glVertexAttribDivisor(2, 1)
            glVertexAttribPointer(
                3, 2, GL_FLOAT, False, stride, ctypes.c_void_p(3 * ctypes.sizeof(ctypes.c_float))
            )
            glEnableVertexAttribArray(3)
            glVertexAttribDivisor(3, 1)
            glVertexAttribPointer(
                4, 2, GL_FLOAT, False, stride, ctypes.c_void_p(5 * ctypes.sizeof(ctypes.c_float))
            )
            glEnableVertexAttribArray(4)
            glVertexAttribDivisor(4, 1)
            glVertexAttribPointer(
                5, 4, GL_FLOAT, False, stride, ctypes.c_void_p(7 * ctypes.sizeof(ctypes.c_float))
            )
            glEnableVertexAttribArray(5)
            glVertexAttribDivisor(5, 1)
            glVertexAttribPointer(
                6, 3, GL_FLOAT, False, stride, ctypes.c_void_p(11 * ctypes.sizeof(ctypes.c_float))
            )
            glEnableVertexAttribArray(6)
            glVertexAttribDivisor(6, 1)

        self.text_instance_vbo = glGenBuffers(1)
        bind_text_instances(self.text_vao, self.text_instance_vbo, self.text_instances)
        self.text_dynamic_instance_vbo = glGenBuffers(1)
        bind_text_instances(
            self.text_dynamic_vao, self.text_dynamic_instance_vbo, self.text_dynamic_instances
        )

        self.atlas_texture = self._load_atlas_texture()

    def resizeGL(self, width: int, height: int) -> None:
        """Handle GL viewport updates on resize.

        Args:
            width: Widget width in pixels.
            height: Widget height in pixels.

        Returns:
            None.
        """
        dpr = self.devicePixelRatioF()
        glViewport(0, 0, max(int(width * dpr), 1), max(int(height * dpr), 1))

    def paintGL(self) -> None:
        """Render the scene for the current frame.

        Returns:
            None.
        """
        if not self.line_program:
            return
        now_utc = time.time()
        delta_ms = (now_utc - self._last_frame_time) * 1000.0
        self._last_frame_time = now_utc
        if delta_ms > 0.0:
            fps = 1000.0 / delta_ms
            if self._fps_smoothed <= 0.0:
                self._fps_smoothed = fps
            else:
                self._fps_smoothed += (fps - self._fps_smoothed) * self._fps_alpha

        bg = self.palette().color(QtGui.QPalette.ColorRole.Window)
        r, g, b, _ = bg.getRgbF()
        # Keep the GL surface opaque to avoid translucent compositing artifacts.
        glClearColor(float(r), float(g), float(b), 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        if self._intel_status_active:
            show_intel_minutes = bool(int(now_utc) % 2)
            if show_intel_minutes != self._show_intel_minutes:
                self._show_intel_minutes = show_intel_minutes
                self._text_dynamic_rebuild_pending = True
        elif self._show_intel_minutes:
            self._show_intel_minutes = False
            self._text_dynamic_rebuild_pending = True
        if self._text_rebuild_pending:
            self._refresh_text_instances(now_utc)
            self._text_rebuild_pending = False
            self._text_dynamic_rebuild_pending = False
        elif self._text_dynamic_rebuild_pending:
            self._refresh_text_dynamic_instances(now_utc)
            self._text_dynamic_rebuild_pending = False

        self._system_rebuild_pending = any( sys.is_dirty for sys in self.systems )
        if self._system_rebuild_pending:
            self._refresh_system_instances()
            self._system_rebuild_pending = False
        dpr = self.devicePixelRatioF()
        screen_width = max(int(self.width() * dpr), 1)
        screen_height = max(int(self.height() * dpr), 1)
        glViewport(0, 0, screen_width, screen_height)
        aspect = screen_width / screen_height

        half_w = self.base_span * aspect
        half_h = self.base_span
        if self.mouse_3d:
            proj = perspective(math.radians(45.0), float(aspect))
            self.camera_target[0] = self.target[0]
            self.camera_target[1] = self.target[1]
            target = self.camera_target
            dir_vec = np.array(
                [
                    math.cos(self.orbit_pitch) * math.sin(self.orbit_yaw),
                    math.sin(self.orbit_pitch),
                    math.cos(self.orbit_pitch) * math.cos(self.orbit_yaw),
                ],
                dtype=np.float32,
            )
            eye = target + dir_vec * float(self.camera_distance)
            view = look_at(eye, target, np.array([0.0, 1.0, 0.0], dtype=np.float32))
            label_scale = 0.1 / self.zoom
            line_proj = proj
            system_proj = proj
        else:
            proj = ortho(
                float(-half_w),
                float(half_w),
                float(-half_h),
                float(half_h),
                -20.0,
                20.0,
            )
            view = np.eye(4, dtype=np.float32)
            view[0, 0] = self.zoom
            view[1, 1] = self.zoom
            view[3, 0] = self.target[0] * self.zoom
            view[3, 1] = self.target[1] * self.zoom
            label_scale = self.zoom / self.base_zoom if self.base_zoom else 1.0

            # Two layers: connections on one, all system visuals on the other.
            line_proj = proj.copy()
            system_proj = proj.copy()
        depth_enabled = 1.0 if self.mouse_3d else 0.0
        depth_scale = 0.1

        line_thickness_scaled = float(max(0.5, self.line_thickness * label_scale))

        if True and (
            self.line_vertices.size
            or self.line_vertices_cross_constellation.size
            or self.line_vertices_cross_region.size )        :
            glDisable(GL_DEPTH_TEST)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glUseProgram(self.line_program)
            glPolygonOffset(0.1, 20.0)
            glUniformMatrix4fv(self.u_line_view, 1, False, view)
            glUniformMatrix4fv(self.u_line_proj, 1, False, line_proj)
            glUniform2f(self.u_line_screen, float(screen_width), float(screen_height))
            glUniform1f(self.u_line_thickness, line_thickness_scaled)

            if self.line_vertices.size:
                r, g, b, _ = PySide6.QtGui.QColor("#c0c0c0").getRgbF()
                glUniform3f(self.u_line_color, r, g, b)
                glBindVertexArray(self.line_vao)
                glDrawArrays(GL_LINES, 0, self.line_vertices.size // 3)
            if self.line_vertices_cross_constellation.size:
                r, g, b, _ = PySide6.QtGui.QColor("#60ff0000").getRgbF()
                glUniform3f(self.u_line_color, r, g, b)
                glBindVertexArray(self.line_constellation_vao)
                glDrawArrays(GL_LINES, 0, self.line_vertices_cross_constellation.size // 3)
            if self.line_vertices_cross_region.size:
                r, g, b, _ = PySide6.QtGui.QColor("#c71585").getRgbF()
                glUniform3f(self.u_line_color, r, g, b)
                glBindVertexArray(self.line_region_vao)
                glDrawArrays(GL_LINES, 0, self.line_vertices_cross_region.size // 3)

        if self.show_jumpbridges  and self.bridge_line_vertices.size:
            glDisable(GL_DEPTH_TEST)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glUseProgram(self.line_program)
            glPolygonOffset(0.1, 20.0)
            glUniformMatrix4fv(self.u_line_view, 1, False, view)
            glUniformMatrix4fv(self.u_line_proj, 1, False, line_proj)
            glUniform2f(self.u_line_screen, float(screen_width), float(screen_height))
            glUniform1f(self.u_line_thickness, line_thickness_scaled)
            r, g, b, _ = PySide6.QtGui.QColor("#7cfc00").getRgbF()
            glUniform3f(self.u_line_color, r, g, b)
            glBindVertexArray(self.bridge_line_vao)
            glDrawArrays(GL_LINES, 0, self.bridge_line_vertices.size // 3)

        if self.system_instance_count:
            glEnable(GL_POLYGON_OFFSET_FILL)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glUseProgram(self.system_program)
            glPolygonOffset(0.1, 4.0)
            glUniformMatrix4fv(self.u_system_view, 1, False, view)
            glUniformMatrix4fv(self.u_system_proj, 1, False, system_proj)
            glUniform2f(self.u_system_screen, float(screen_width), float(screen_height))
            glUniform2f(self.u_system_size, float(self.label_width), float(self.label_height))
            glUniform1f(self.u_system_radius, float(self.label_radius))
            glUniform1f(self.u_system_scale, float(label_scale))
            glUniform1f(self.u_system_depth_scale, float(depth_scale))
            glUniform1f(self.u_system_depth_enabled, float(depth_enabled))
            glUniform1f(self.u_system_border_thickness, 1.5)
            glUniform1f(self.u_system_outer_border_thickness, 1.5)
            glUniform1f(self.u_system_aa_margin, 1.0)
            glUniform4f(
                self.u_system_fill,
                float(self.rect_fill_color[0]),
                float(self.rect_fill_color[1]),
                float(self.rect_fill_color[2]),
                float(self.rect_fill_color[3]),
            )
            glUniform4f(
                self.u_system_intel_color_green,
                float(self.intel_color_green[0]),
                float(self.intel_color_green[1]),
                float(self.intel_color_green[2]),
                float(self.intel_color_green[3]),
            )
            glUniform4f(
                self.u_system_intel_color_red,
                float(self.intel_color_red[0]),
                float(self.intel_color_red[1]),
                float(self.intel_color_red[2]),
                float(self.intel_color_red[3]),
            )
            intel_now = now_utc - self.intel_time_base
            glUniform1f(self.u_system_intel_now, float(intel_now))
            glUniform1f(self.u_system_intel_duration, float(self.intel_fade_seconds))
            r, g, b, a = PySide6.QtGui.QColor("#ffc0c0c0").getRgbF() # border of system rect
            glUniform4f(self.u_system_border, r, g, b, a )
            r, g, b, a = PySide6.QtGui.QColor("#800088ff").getRgbF() # ice belt color
            glUniform4f(self.u_system_outer_border, r, g, b, a)
            glUniform1f(self.u_system_halo_radius, float(self.halo_radius_factor))
            glUniform4f(
                self.u_system_halo_color_marked,
                float(self.halo_color_marked[0]),
                float(self.halo_color_marked[1]),
                float(self.halo_color_marked[2]),
                float(self.halo_color_marked[3]),
            )
            glUniform4f(
                self.u_system_halo_color_kill,
                float(self.halo_color_kill[0]),
                float(self.halo_color_kill[1]),
                float(self.halo_color_kill[2]),
                float(self.halo_color_kill[3]),
            )
            glUniform4f(
                self.u_system_halo_color_monitored,
                float(self.halo_color_monitored[0]),
                float(self.halo_color_monitored[1]),
                float(self.halo_color_monitored[2]),
                float(self.halo_color_monitored[3]),
            )
            glUniform4f(
                self.u_system_halo_color_populated,
                float(self.halo_color_populated[0]),
                float(self.halo_color_populated[1]),
                float(self.halo_color_populated[2]),
                float(self.halo_color_populated[3]),
            )
            glUniform4f(
                self.u_system_halo_color_contested,
                float(self.halo_color_contested[0]),
                float(self.halo_color_contested[1]),
                float(self.halo_color_contested[2]),
                float(self.halo_color_contested[3]),
            )
            glUniform4f(
                self.u_system_halo_color_incursion,
                float(self.halo_color_incursion[0]),
                float(self.halo_color_incursion[1]),
                float(self.halo_color_incursion[2]),
                float(self.halo_color_incursion[3]),
            )
            glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 2, self.system_ssbo)
            glBindVertexArray(self.system_vao)
            glDisable(GL_DEPTH_TEST)
            glBlendFuncSeparate(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_ONE, GL_ONE)
            glUniform1i(self.u_system_pass, 0)
            glDrawArraysInstanced(GL_TRIANGLE_STRIP, 0, 4, self.system_instance_count)
            glEnable(GL_DEPTH_TEST)
            glBlendFuncSeparate(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_ONE, GL_ONE)
            glUniform1i(self.u_system_pass, 1)
            glDrawArraysInstanced(GL_TRIANGLE_STRIP, 0, 4, self.system_instance_count)

        if True and self.structure_draws:
            glEnable(GL_DEPTH_TEST)
            glEnable(GL_POLYGON_OFFSET_FILL)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glUseProgram(self.structure_program)
            glPolygonOffset(0.1, 2.0)
            glUniformMatrix4fv(self.u_struct_view, 1, False, view)
            glUniformMatrix4fv(self.u_struct_proj, 1, False, system_proj)
            glUniform2f(self.u_struct_screen, float(screen_width), float(screen_height))
            glUniform1f(self.u_struct_scale, float(label_scale))
            glUniform1f(self.u_struct_depth_scale, float(depth_scale))
            glUniform1f(self.u_struct_depth_enabled, float(depth_enabled))
            # Fill pass (match label fill)
            glUniform3f(
                self.u_struct_color,
                float(self.rect_fill_color[0]),
                float(self.rect_fill_color[1]),
                float(self.rect_fill_color[2]),
            )
            for draw in self.structure_draws:
                if draw["fill_vao"] and draw["fill_count"]:
                    glBindVertexArray(draw["fill_vao"])
                    glDrawArraysInstanced(GL_TRIANGLES, 0, draw["fill_count"], draw["instance_count"])
            # Border pass in white
            glUniform3f(self.u_struct_color, 1.0, 1.0, 1.0)
            for draw in self.structure_draws:
                if draw["border_vao"] and draw["border_count"]:
                    glBindVertexArray(draw["border_vao"])
                    glDrawArraysInstanced(GL_LINES, 0, draw["border_count"], draw["instance_count"])

        if True and ((self.text_instance_count or self.text_dynamic_instance_count) and self.atlas_texture):
            if self.mouse_3d:
                text_alpha_scale = 1.0
            else:
                # Fade text out at tiny zoom levels to avoid minified atlas shimmer.
                fade_start = float(self.text_fade_start_scale)
                fade_end = max(float(self.text_fade_end_scale), fade_start + 1e-6)
                if label_scale <= fade_start:
                    text_alpha_scale = 0.0
                elif label_scale >= fade_end:
                    text_alpha_scale = 1.0
                else:
                    text_alpha_scale = (label_scale - fade_start) / (fade_end - fade_start)
            if text_alpha_scale > 0.001:
                glEnable(GL_DEPTH_TEST)
                glEnable(GL_POLYGON_OFFSET_FILL)
                glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
                glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_CONSTANT_COLOR)
                glUseProgram(self.text_program)
                glPolygonOffset(0.1, -2.0)
                glUniformMatrix4fv(self.u_text_view, 1, False, view)
                glUniformMatrix4fv(self.u_text_proj, 1, False, system_proj)
                glUniform2f(self.u_screen, float(screen_width), float(screen_height))
                glUniform1f(self.u_text_scale, float(label_scale))
                glUniform1f(self.u_text_depth_scale, float(depth_scale))
                glUniform1f(self.u_text_depth_enabled, float(depth_enabled))
                glUniform1f(self.u_text_alpha_scale, float(text_alpha_scale))
                glActiveTexture(GL_TEXTURE0)
                glBindTexture(GL_TEXTURE_2D, self.atlas_texture)
                glUniform1i(self.u_atlas, 0)
                if self.text_instance_count:
                    glBindVertexArray(self.text_vao)
                    glDrawArraysInstanced(GL_TRIANGLE_STRIP, 0, 4, self.text_instance_count)
                if self.text_dynamic_instance_count:
                    glBindVertexArray(self.text_dynamic_vao)
                    glDrawArraysInstanced(
                        GL_TRIANGLE_STRIP, 0, 4, self.text_dynamic_instance_count
                    )
                glEnable(GL_DEPTH_TEST)
                glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        glDisable(GL_POLYGON_OFFSET_FILL)
        self._draw_hud()
        #self.update()


    def _update_hovered_system(self) -> None:
        """Update the cached hovered system based on the last mouse position.

        Returns:
            None.
        """
        if self._last_mouse_pos is None:
            self._hovered_system = None
            return
        hovered_id = self.objectUnderMouse(self._last_mouse_pos)
        self._hovered_system = self._system_by_id(hovered_id)

    def _resolve_hud_labels(self) -> tuple[str, str]:
        """Return region/constellation labels for the HUD.

        Returns:
            Tuple of (region_name, constellation_name).
        """
        system = self._hovered_system
        if system is None:
            return "-", "-"
        record = system.record or {}
        region_name = record.get("regionName") or record.get("region")
        if not region_name:
            region_id = record.get("regionID")
            region_name = f"ID {region_id}" if region_id is not None else "Unknown"
        const_name = record.get("constellationName") or record.get("constellation")
        if not const_name:
            const_id = record.get("constellationID")
            const_name = f"ID {const_id}" if const_id is not None else "Unknown"
        return str(region_name), str(const_name)

    def _draw_hud(self) -> None:
        """Draw a HUD overlay for region/constellation and FPS.

        Returns:
            None.
        """
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing, True)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)

        font = painter.font()
        if font.pointSizeF() > 0:
            font.setPointSizeF(font.pointSizeF() * 0.9)
        painter.setFont(font)

        region_name, const_name = self._resolve_hud_labels()
        fps_text = "--" if self._fps_smoothed <= 0.0 else f"{self._fps_smoothed:4.1f}"
        lines = [
            f"Region: {region_name}",
            f"Constellation: {const_name}",
            f"FPS: {fps_text}",
        ]

        metrics = painter.fontMetrics()
        line_height = metrics.height()
        text_width = max(metrics.horizontalAdvance(line) for line in lines)
        padding = int(self._hud_padding)
        rect_width = text_width + padding * 2
        rect_height = line_height * len(lines) + padding * 2
        rect = QtCore.QRectF(12.0, 12.0, float(rect_width), float(rect_height))

        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(self._hud_bg)
        painter.drawRoundedRect(rect, float(self._hud_radius), float(self._hud_radius))

        painter.setPen(self._hud_text)
        x = rect.left() + padding
        y = rect.top() + padding + metrics.ascent()
        for line in lines:
            painter.drawText(QtCore.QPointF(x, y), line)
            y += line_height
        painter.end()

    def _load_atlas_texture(self) -> int:
        """Upload the atlas image as an OpenGL texture.

        Returns:
            OpenGL texture handle, or 0 on failure.
        """
        image = QtGui.QImage(self.atlas["image"])
        if image.isNull():
            return 0
        image = image.convertToFormat(QtGui.QImage.Format.Format_RGBA8888)
        width = image.width()
        height = image.height()
        data = image.bits() # .asstring(image.sizeInBytes())

        tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex)
        # Use mipmaps to stabilize atlas minification when zooming far out.
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGBA,
            width,
            height,
            0,
            GL_RGBA,
            GL_UNSIGNED_BYTE,
            data,
        )
        glGenerateMipmap(GL_TEXTURE_2D)
        return tex

    def _mark_factor(self, system_idx: int) -> float:
        """Convert remaining mark time to a [0, 1] weight.

        Args:
            system_idx: Index of the system in `self.systems`.

        Returns:
            Normalized mark weight.
        """
        mark_ms = self.mark_timers.get(system_idx, 0.0)
        if mark_ms <= 0.0:
            return 0.0
        return max(0.0, min(mark_ms / 10000.0, 1.0))

    def _kill_factor(self, system_idx: int) -> float:
        """Convert remaining kill time to a [0, 1] weight.

        Args:
            system_idx: Index of the system in `self.systems`.

        Returns:
            Normalized kill weight.
        """
        kill_ms = self.kill_timers.get(system_idx, 0.0)
        if kill_ms <= 0.0:
            return 0.0
        return max(0.0, min(kill_ms, 1.0))
        #return max(0.0, min(kill_ms / 10000.0, 1.0))

    def _tick_kill_timers(self, delta_ms: float) -> bool:
        """Decrease kill timers by elapsed milliseconds.

        Args:
            delta_ms: Elapsed time in milliseconds.

        Returns:
            True if any timer changed, else False.
        """
        if delta_ms <= 0.0:
            return False
        changed = False
        for idx, remaining in list(self.kill_timers.items()):
            if remaining <= 0.0:
                continue
            updated = max(0.0, remaining - delta_ms)
            if updated != remaining:
                self.kill_timers[idx] = updated
                changed = True
        return changed

    def _refresh_system_instances(self) -> None:
        """Update GPU system instances after data changes.

        Returns:
            None.
        """
        self.mark_timers = {idx: max(0.0, float(sys.marker)) for idx, sys in enumerate(self.systems)}
        self.kill_timers = {idx: max(0.0, float(sys.hasKill)) for idx, sys in enumerate(self.systems)}
        self.system_instances = self._build_system_instances()
        self.system_instance_count = (
            self.system_instances.shape[0] if self.system_instances.size else 0
        )
        if self.system_ssbo:
            glBindBuffer(GL_SHADER_STORAGE_BUFFER, self.system_ssbo)
            if self.system_instances.size:
                data = self.system_instances
                size = self.system_instances.nbytes
            else:
                data = None
                size = 0
            glBufferData(GL_SHADER_STORAGE_BUFFER, size, data, GL_DYNAMIC_DRAW)

    def _refresh_text_instances(self, now: Optional[float] = None) -> None:
        """Update GPU text instances after label text changes.

        Args:
            now: Optional timestamp used for intel aging.

        Returns:
            None.
        """
        self.text_instances, self.text_dynamic_instances = self._build_text_instances(now)
        self.text_instance_count = self.text_instances.shape[0] if self.text_instances.size else 0
        self.text_dynamic_instance_count = self.text_dynamic_instances.shape[0] if self.text_dynamic_instances.size else 0

        if self.text_instance_vbo:
            glBindBuffer(GL_ARRAY_BUFFER, self.text_instance_vbo)
            glBufferData(
                GL_ARRAY_BUFFER,
                self.text_instances.nbytes,
                self.text_instances,
                GL_DYNAMIC_DRAW,
            )
        if self.text_dynamic_instance_vbo:
            glBindBuffer(GL_ARRAY_BUFFER, self.text_dynamic_instance_vbo)
            glBufferData(
                GL_ARRAY_BUFFER,
                self.text_dynamic_instances.nbytes,
                self.text_dynamic_instances,
                GL_DYNAMIC_DRAW,
            )

    def _refresh_text_dynamic_instances(self, now: Optional[float] = None) -> None:
        """Update GPU text instances for the dynamic status line.

        Args:
            now: Optional timestamp used for intel aging.

        Returns:
            None.
        """
        self.text_dynamic_instances = self._build_text_dynamic_instances(now)
        self.text_dynamic_instance_count = (
            self.text_dynamic_instances.shape[0] if self.text_dynamic_instances.size else 0
        )
        if self.text_dynamic_instance_vbo:
            glBindBuffer(GL_ARRAY_BUFFER, self.text_dynamic_instance_vbo)
            glBufferData(
                GL_ARRAY_BUFFER,
                self.text_dynamic_instances.nbytes,
                self.text_dynamic_instances,
                GL_DYNAMIC_DRAW,
            )

    def _build_system_instances(self) -> np.ndarray:
        """Build per-system SSBO data for the unified system shader.

        Returns:
            Float32 array of per-system SSBO entries.
        """
        instances: List[List[float]] = []

        def coerce_color(
            value: None|Tuple[float, float, float, float] | Tuple[float, float, float] | float | list
        ) -> Tuple[float, float, float, float]:
            """Normalize honeycomb color inputs to RGBA floats.

            Args:
                value: RGBA tuple, RGB tuple, alpha-only float, or list.

            Returns:
                RGBA color tuple.
            """
            if value is None:
                return 0.0, 0.0, 0.0, 0.0
            elif isinstance(value, str):
                r,g,b,a = PySide6.QtGui.QColor(value).getRgbF()
                return r,g,b,a
            elif isinstance(value, PySide6.QtGui.QColor):
                r,g,b,a = value.getRgbF()
                return r,g,b,a
            elif isinstance(value, (int, float)):
                alpha = float(value)
                return 0.16, 0.2, 0.23, max(0.0, min(1.0, alpha))
            elif isinstance(value, (tuple, list)):
                if len(value) == 4 and all(isinstance(v, (int, float)) for v in value):
                    r, g, b, a = value
                    return float(r),float(g),float(b),max(0.0, min(1.0, float(a)))
                if len(value) == 3 and all(isinstance(v, (int, float)) for v in value):
                    r, g, b = value
                    return float(r), float(g), float(b), 1.0
            return 0.16, 0.2, 0.23, 1.0

        utc_now = time.time()
        self._intel_status_active = False
        for sys in self.systems:
            sys.clr_dirty()
            intel_status = sys.intel_status
            intel_time = 0.0
            if intel_status > 0:
                self._intel_status_active = True
                intel_time = sys.intel_status_alpha(utc_now)
            if  sys.marker > 0.0:
                delta = sys.marker-sys.marker_start
                if sys.marker > utc_now and delta > 0.0:
                    mark_factor = max(0.0,(sys.marker - utc_now)/delta)
                else:
                    sys.marker_start = 0.0
                    sys.marker = 0.0
                    mark_factor = 0.0
            else:
                mark_factor =0.0
            if sys.hasKill > 0.0:
                kill_factor = max(0.0,(sys.hasKill - utc_now)/600.0)
            else:
                kill_factor = 0.0
            color = coerce_color(sys.marking_color)
            margin = max(0.0, float(sys.marking_scale*24.0))
            monitored = 1.0 if sys.isMonitored() else 0.0
            char_located = 1.0 if bool(sys._locatedCharacters) else 0.0
            if char_located == 1.0:
                pass
            instances.append(
                [
                    sys.x,                  #x
                    sys.y,                  #y
                    sys.z,                  #z
                    intel_status,           #w
                    intel_time,             #x
                    mark_factor,            #y
                    monitored,              #z
                    char_located,           #w
                    1.0 if sys.hasCampaigns else 0.0,
                    1.0 if sys.hasIncursion else 0.0,
                    kill_factor,
                    margin,
                    color[0],
                    color[1],
                    color[2],
                    color[3],
                    1.0 if sys.has_ice_belt else 0.0,
                    1.0 if sys.hasIncursionBoss else 0.0,
                    1.0 if sys.has_upwell_cyno_jammer else 0.0,
                    1.0 if sys.has_upwell_cyno_beacon else 0.0,
            ]
            )

        if not self._intel_status_active and self._show_intel_minutes:
            self._show_intel_minutes = False
            self._system_rebuild_pending = True
            self._text_rebuild_pending = True
            self._text_dynamic_rebuild_pending = True

        if not instances:
            return np.array([], dtype=np.float32)
        return np.array(instances, dtype=np.float32)

    def _build_structure_vertices(self) -> dict[int, dict[str, np.ndarray]]:
        """Convert structure templates into pixel vertices anchored to labels.

        Returns:
            Mapping of structure IDs to fill/border vertex arrays.
        """
        vertices: dict[int, dict[str, np.ndarray]] = {}
        anchor_x = self.label_width * 0.5
        target_h = self.label_height * 0.9 * 0.7
        target_w = self.label_width * 0.35 * 0.7
        for key, (segments, rows, cols, stars, plus_row, plus_col) in STRUCTURE_TEMPLATES.items():
            if rows <= 0 or cols <= 0:
                vertices[key] = {"fill": np.array([], dtype=np.float32), "border": np.array([], dtype=np.float32)}
                continue
            cell = min(target_h / rows, target_w / cols)
            min_x = min(min(x0, x1) for x0, _, x1, _ in segments) if segments else 0.0
            offset_x = -min_x if min_x < 0 else 0.0
            border_verts: List[float] = []
            for x0, y0, x1, y1 in segments:
                px0 = anchor_x + (x0 + offset_x) * cell
                py0 = y0 * cell
                px1 = anchor_x + (x1 + offset_x) * cell
                py1 = y1 * cell
                border_verts.extend([px0, py0, px1, py1])
            # Fill all interior cells (including enclosed gaps) using flood fill.
            star_set = set(stars)
            empties = {(r, c) for r in range(rows) for c in range(cols) if (r, c) not in star_set}
            exterior: set[Tuple[int, int]] = set()
            stack: List[Tuple[int, int]] = []
            for c in range(cols):
                if (0, c) in empties:
                    stack.append((0, c))
                if (rows - 1, c) in empties:
                    stack.append((rows - 1, c))
            for r in range(rows):
                if (r, 0) in empties:
                    stack.append((r, 0))
                if (r, cols - 1) in empties:
                    stack.append((r, cols - 1))
            while stack:
                r, c = stack.pop()
                if (r, c) in exterior:
                    continue
                if (r, c) not in empties:
                    continue
                exterior.add((r, c))
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols and (nr, nc) not in exterior:
                        stack.append((nr, nc))
            interior = empties - exterior
            fill_cells = star_set | interior

            fill_verts: List[float] = []
            for r, c in fill_cells:
                x0 = (c - plus_col) + offset_x
                y0 = (r - plus_row)
                x1 = x0 + 1.0
                y1 = y0 + 1.0
                px0 = anchor_x + x0 * cell
                py0 = y0 * cell
                px1 = anchor_x + x1 * cell
                py1 = y1 * cell
                fill_verts.extend(
                    [
                        px0,
                        py0,
                        px1,
                        py0,
                        px1,
                        py1,
                        px0,
                        py0,
                        px1,
                        py1,
                        px0,
                        py1,
                    ]
                )
            vertices[key] = {
                "fill": np.array(fill_verts, dtype=np.float32) if fill_verts else np.array([], dtype=np.float32),
                "border": np.array(border_verts, dtype=np.float32) if border_verts else np.array([], dtype=np.float32),
            }
        return vertices

    def _build_structure_instances(self) -> dict[int, np.ndarray]:
        """Collect per-structure centers for instanced drawing.

        Returns:
            Mapping of structure IDs to center arrays.
        """
        instances: dict[int, List[List[float]]] = {1: [], 2: [], 3: []}
        for sys in self.systems:
            if sys.structure in instances and sys.structure > 0:
                instances[sys.structure].append([sys.x, sys.y, sys.z])
        return {
            key: (np.array(vals, dtype=np.float32) if vals else np.array([], dtype=np.float32))
            for key, vals in instances.items()
        }

    def _compute_label_size(self) -> Tuple[float, float]:
        """Return fixed label dimensions.

        Returns:
            Tuple of (width, height) in pixels.
        """
        #return System.ELEMENT_WIDTH,System.ELEMENT_HEIGHT
        return 108.0, 48.0

    def _build_text_instances(
        self, now: Optional[float] = None, include_static: bool = True
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Build per-glyph instance data for static and dynamic system labels.

        Args:
            now: Optional timestamp used for intel aging.
            include_static: Whether to include static label lines.

        Returns:
            Tuple of (static_instances, dynamic_instances) arrays.
        """
        if now is None:
            now = time.time()
        glyphs = self.atlas.get("glyphs", {})
        atlas_w, atlas_h = self.atlas.get("size", [1, 1])
        atlas_w = max(float(atlas_w), 1.0)
        atlas_h = max(float(atlas_h), 1.0)
        primary_scale = self.atlas_scale * self.font_scale
        secondary_scale = self.atlas_scale * self.secondary_text_scale * self.font_scale
        static_instances: List[List[float]] = []
        dynamic_instances: List[List[float]] = []
        #box_w = self.label_width - self.label_padding * 2.0
        box_w = self.label_width * 1.2
        line_gap = self.label_line_gap
        primary_ascent = self.label_ascent
        secondary_ascent = self.label_ascent * self.secondary_text_scale
        primary_line_height = self.label_line_height
        secondary_line_height = self.label_line_height * self.secondary_text_scale
        half_height = self.label_height * 0.5
        outer_gap = self.label_padding + line_gap
        base_color = (0.95, 0.95, 0.98)
        accent_color = (1.0, 0.65, 0.25)
        alert_color = (0.95, 0.25, 0.25)

        def add_line(
            instances: List[List[float]],
            sys,
            text: str,
            line_y: float,
            align: str,
            color: Tuple[float, float, float],
            scale: float,
        ) -> None:
            """Build glyph instances for a single label line.

            Args:
                sys: System whose label is being drawn.
                text: Text content for the line.
                line_y: Baseline Y offset relative to the label center.
                align: Horizontal alignment ('left', 'right', 'center').
                color: RGB tuple applied to the glyphs.
                scale: Glyph scale factor for the line.

            Returns:
                None.
            """
            if not text:
                return
            line_width = 0.0
            for ch in text:
                glyph = glyphs.get(ch) or glyphs.get("?")
                if glyph:
                    line_width += float(glyph["advance"]) * scale
            if line_width <= 0.0:
                return
            if align == "left":
                pen_x = -box_w / 2.0
            elif align == "right":
                pen_x = box_w / 2.0 - line_width
            else:
                pen_x = -box_w / 2.0 + (box_w - line_width) / 2.0
            for ch in text:
                if ch not in glyphs:
                    ch = "?"
                glyph = glyphs.get(ch)
                if not glyph:
                    continue
                adv = float(glyph["advance"]) * scale
                if glyph["w"] <= 0 or glyph["h"] <= 0:
                    pen_x += adv
                    continue
                offset_x = pen_x + float(glyph["bearing_x"]) * scale
                offset_y = line_y + float(glyph["bearing_y"]) * scale
                size_x = float(glyph["w"]) * scale
                size_y = float(glyph["h"]) * scale
                glyph_x = float(glyph["x"])
                glyph_y = float(glyph["y"])
                glyph_w = float(glyph["w"])
                glyph_h = float(glyph["h"])
                inset_u = min(0.5, max((glyph_w - 1.0) * 0.5, 0.0))
                inset_v = min(0.5, max((glyph_h - 1.0) * 0.5, 0.0))
                u0 = (glyph_x + inset_u) / atlas_w
                v0 = (glyph_y + inset_v) / atlas_h
                u1 = (glyph_x + glyph_w - inset_u) / atlas_w
                v1 = (glyph_y + glyph_h - inset_v) / atlas_h
                us = max(u1 - u0, 1.0 / atlas_w)
                vs = max(v1 - v0, 1.0 / atlas_h)
                instances.append(
                    [
                        sys.x,
                        sys.y,
                        sys.z,
                        offset_x,
                        offset_y,
                        size_x,
                        size_y,
                        u0,
                        v0,
                        us,
                        vs,
                        float(color[0]),
                        float(color[1]),
                        float(color[2]),
                    ]
                )
                pen_x += adv

        intel_cleared = False
        for sys in self.systems:
            intel_status = sys.intel_status
            was_intel = intel_status != IntelStatus.NONE
            total_h = primary_line_height * 2.0 + line_gap
            baseline = -total_h / 2.0 + primary_ascent
            line1_y = baseline
            line2_y = baseline + primary_line_height + line_gap
            outside_offset = secondary_line_height * 0.5
            above_y = -half_height - outer_gap + secondary_ascent - outside_offset
            below_y = half_height + outer_gap + secondary_ascent - outside_offset
            if include_static:
                add_line(static_instances, sys, sys.name, line1_y, "center", base_color, primary_scale)
            status_text = sys.ticker
            if was_intel and self._show_intel_minutes:
                intel_text = sys.intel_status_time_string(now)
                if intel_text:
                    status_text = intel_text
            if was_intel and intel_status != IntelStatus.NONE:
                add_line(dynamic_instances, sys, status_text, line2_y, "center", base_color, primary_scale)
            elif include_static:
                add_line(static_instances, sys, status_text, line2_y, "center", base_color, primary_scale)
            if was_intel and intel_status == IntelStatus.NONE:
                intel_cleared = True
            if include_static:
                if self.show_timers:
                    add_line(static_instances, sys, sys.sec_state, above_y, "left", accent_color, secondary_scale)
                    add_line(static_instances, sys, sys.timer, above_y, "right", accent_color, secondary_scale)
                if self.show_statistic:
                    add_line(
                        static_instances,
                        sys,
                        sys.statistics,
                        below_y,
                        "center",
                        alert_color,
                        secondary_scale,
                    )
        if intel_cleared:
            self._system_rebuild_pending = True
            if not include_static:
                self._text_rebuild_pending = True
        static_array = (
            np.array(static_instances, dtype=np.float32)
            if static_instances and include_static
            else np.array([], dtype=np.float32)
        )
        dynamic_array = (
            np.array(dynamic_instances, dtype=np.float32)
            if dynamic_instances
            else np.array([], dtype=np.float32)
        )
        return static_array, dynamic_array

    def _build_text_dynamic_instances(self, now: Optional[float] = None) -> np.ndarray:
        """Build per-glyph instance data for dynamic status lines only.

        Args:
            now: Optional timestamp used for intel aging.

        Returns:
            Float32 instance array for dynamic glyphs.
        """
        _, dynamic_instances = self._build_text_instances(now, include_static=False)
        return dynamic_instances

    def _build_hud_instances(
        self, text: str, pen_x: float, pen_y: float, color: Tuple[float, float, float]
    ) -> np.ndarray:
        """Build per-glyph instance data for HUD text.

        Args:
            text: HUD text to render.
            pen_x: Horizontal offset in pixels.
            pen_y: Vertical offset in pixels.
            color: RGB tuple applied per glyph.

        Returns:
            Float32 instance array for instanced glyphs.
        """
        glyphs = self.atlas.get("glyphs", {})
        atlas_w, atlas_h = self.atlas.get("size", [1, 1])
        atlas_w = max(float(atlas_w), 1.0)
        atlas_h = max(float(atlas_h), 1.0)
        scale = self.atlas_scale * self.font_scale
        instances: List[List[float]] = []
        center = [-1.0, 1.0, 0.0]
        cursor_x = pen_x
        cursor_y = pen_y
        for ch in text:
            if ch not in glyphs:
                ch = "?"
            glyph = glyphs.get(ch)
            if not glyph:
                continue
            adv = float(glyph["advance"]) * scale
            if glyph["w"] <= 0 or glyph["h"] <= 0:
                cursor_x += adv
                continue
            offset_x = cursor_x + float(glyph["bearing_x"]) * scale
            offset_y = cursor_y + float(glyph["bearing_y"]) * scale
            size_x = float(glyph["w"]) * scale
            size_y = float(glyph["h"]) * scale
            glyph_x = float(glyph["x"])
            glyph_y = float(glyph["y"])
            glyph_w = float(glyph["w"])
            glyph_h = float(glyph["h"])
            inset_u = min(0.5, max((glyph_w - 1.0) * 0.5, 0.0))
            inset_v = min(0.5, max((glyph_h - 1.0) * 0.5, 0.0))
            u0 = (glyph_x + inset_u) / atlas_w
            v0 = (glyph_y + inset_v) / atlas_h
            u1 = (glyph_x + glyph_w - inset_u) / atlas_w
            v1 = (glyph_y + glyph_h - inset_v) / atlas_h
            us = max(u1 - u0, 1.0 / atlas_w)
            vs = max(v1 - v0, 1.0 / atlas_h)
            instances.append(
                [
                    center[0],
                    center[1],
                    center[2],
                    offset_x,
                    offset_y,
                    size_x,
                    size_y,
                    u0,
                    v0,
                    us,
                    vs,
                    float(color[0]),
                    float(color[1]),
                    float(color[2]),
                ]
            )
            cursor_x += adv
        if not instances:
            return np.array([], dtype=np.float32)
        return np.array(instances, dtype=np.float32)

    def _system_by_id(self, system_id: Optional[int]) -> Optional[System]:
        """Return a system by ID when it exists in the current dataset.

        Args:
            system_id: System identifier.

        Returns:
            Matching system or None if not found.
        """
        if system_id is None:
            return None
        system_idx = self.system_index_by_id.get(int(system_id))
        if system_idx is None:
            return None
        return self.systems[system_idx]

    def _cpu_pick_system_id(
        self, mouse_x: float, mouse_y: float, width: int, height: int
    ) -> Optional[int]:
        """CPU fallback for picking a system under the cursor.

        Args:
            mouse_x: Cursor X coordinate.
            mouse_y: Cursor Y coordinate.
            width: Viewport width in pixels.
            height: Viewport height in pixels.

        Returns:
            System ID under the cursor, or None.
        """
        if not self.systems or width <= 0 or height <= 0:
            return None
        if self.mouse_3d:
            aspect = width / float(height)
            proj = perspective(math.radians(45.0), float(aspect)).T
            target = np.array(
                [float(self.target[0]), float(self.target[1]), float(self.camera_target[2])],
                dtype=np.float32,
            )
            dir_vec = np.array(
                [
                    math.cos(self.orbit_pitch) * math.sin(self.orbit_yaw),
                    math.sin(self.orbit_pitch),
                    math.cos(self.orbit_pitch) * math.cos(self.orbit_yaw),
                ],
                dtype=np.float32,
            )
            eye = target + dir_vec * float(self.camera_distance)
            view = look_at(eye, target, np.array([0.0, 1.0, 0.0], dtype=np.float32)).T
            depth_scale = 0.1
            closest_id: Optional[int] = None
            closest_dist = float("inf")
            for sys in self.systems:
                pos = np.array([sys.x, sys.y, sys.z, 1.0], dtype=np.float32)
                view_pos = view @ pos
                depth = float(np.linalg.norm(view_pos[:3]))
                scale = depth_scale / max(depth, 1e-6)
                half_label_w = self.label_width * 0.5 * scale
                half_label_h = self.label_height * 0.5 * scale
                clip = proj @ view_pos
                w = float(clip[3])
                if abs(w) <= 1e-6:
                    continue
                ndc = clip[:3] / w
                if abs(ndc[0]) > 1.1 or abs(ndc[1]) > 1.1 or ndc[2] < -1.1 or ndc[2] > 1.1:
                    continue
                screen_x = (ndc[0] * 0.5 + 0.5) * width
                screen_y = (1.0 - (ndc[1] * 0.5 + 0.5)) * height
                if abs(screen_x - mouse_x) <= half_label_w and abs(screen_y - mouse_y) <= half_label_h:
                    if depth < closest_dist:
                        closest_id = int(sys.system_id)
                        closest_dist = depth
            return closest_id
        aspect = width / float(height)
        half_w = self.base_span * aspect
        half_h = self.base_span
        label_scale = self.zoom / self.base_zoom if self.base_zoom else 1.0
        half_label_w = self.label_width * 0.5 * label_scale
        half_label_h = self.label_height * 0.5 * label_scale
        for sys in self.systems:
            ndc_x = self.zoom * (sys.x + self.target[0]) / half_w
            ndc_y = self.zoom * (sys.y + self.target[1]) / half_h
            screen_x = (ndc_x * 0.5 + 0.5) * width
            screen_y = (1.0 - (ndc_y * 0.5 + 0.5)) * height
            if abs(screen_x - mouse_x) <= half_label_w and abs(screen_y - mouse_y) <= half_label_h:
                return int(sys.system_id)
        return None

    def _gpu_pick_system_id(
        self, mouse_x: float, mouse_y: float, width: int, height: int
    ) -> Optional[int]:
        """Use a compute shader to find the hovered system id.

        Args:
            mouse_x: Cursor X coordinate.
            mouse_y: Cursor Y coordinate.
            width: Viewport width in pixels.
            height: Viewport height in pixels.

        Returns:
            System ID under the cursor, or None.
        """
        if (
            not self.pick_program
            or not self.pick_positions_ssbo
            or not self.pick_distances_ssbo
            or not self.systems
        ):
            return None
        if width <= 0 or height <= 0:
            return None

        count = len(self.systems)
        aspect = width / float(height)
        if self.mouse_3d:
            proj = perspective(math.radians(45.0), float(aspect))
            self.camera_target[0] = self.target[0]
            self.camera_target[1] = self.target[1]
            target = self.camera_target
            dir_vec = np.array(
                [
                    math.cos(self.orbit_pitch) * math.sin(self.orbit_yaw),
                    math.sin(self.orbit_pitch),
                    math.cos(self.orbit_pitch) * math.cos(self.orbit_yaw),
                ],
                dtype=np.float32,
            )
            eye = target + dir_vec * float(self.camera_distance)
            view = look_at(eye, target, np.array([0.0, 1.0, 0.0], dtype=np.float32))
            label_scale = 0.1 / max(self.zoom, 1e-6)
            mode = 1
        else:
            half_w = self.base_span * aspect
            half_h = self.base_span
            proj = ortho(float(-half_w), float(half_w), float(-half_h), float(half_h), -20.0, 20.0)
            view = np.eye(4, dtype=np.float32)
            view[0, 0] = self.zoom
            view[1, 1] = self.zoom
            view[3, 0] = self.target[0] * self.zoom
            view[3, 1] = self.target[1] * self.zoom
            label_scale = self.zoom / self.base_zoom if self.base_zoom else 1.0
            mode = 0

        half_label_base_w = self.label_width * 0.5
        half_label_base_h = self.label_height * 0.5
        if half_label_base_w <= 0.0 or half_label_base_h <= 0.0:
            return None
        depth_scale = 0.1
        depth_enabled = 1.0 if self.mouse_3d else 0.0

        self.makeCurrent()
        try:
            glUseProgram(self.pick_program)
            glUniformMatrix4fv(self.u_pick_view, 1, False, view)
            glUniformMatrix4fv(self.u_pick_proj, 1, False, proj)
            glUniform2f(self.u_pick_screen, float(width), float(height))
            glUniform2f(self.u_pick_mouse, float(mouse_x), float(mouse_y))
            glUniform2f(self.u_pick_half_label_base, float(half_label_base_w), float(half_label_base_h))
            glUniform1f(self.u_pick_label_scale, float(label_scale))
            glUniform1f(self.u_pick_depth_scale, float(depth_scale))
            glUniform1f(self.u_pick_depth_enabled, float(depth_enabled))
            glUniform1i(self.u_pick_count, int(count))
            glUniform1i(self.u_pick_mode, int(mode))
            glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, self.pick_positions_ssbo)
            glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 1, self.pick_distances_ssbo)
            groups = (count + 255) // 256
            glDispatchCompute(groups, 1, 1)
            glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT)
            glBindBuffer(GL_SHADER_STORAGE_BUFFER, self.pick_distances_ssbo)
            data = glGetBufferSubData(
                GL_SHADER_STORAGE_BUFFER,
                0,
                count * ctypes.sizeof(ctypes.c_float),
            )
        finally:
            self.doneCurrent()

        distances = np.frombuffer(data, dtype=np.float32, count=count)
        if distances.size == 0:
            return None
        min_idx = int(np.argmin(distances))
        min_dist = float(distances[min_idx])
        if not np.isfinite(min_dist) or min_dist > 1e30:
            return None
        return int(self.systems[min_idx].system_id)

    def objectUnderMouse(
        self, child_pos: QtCore.QPointF | QtCore.QPoint | Tuple[float, float]
    ) -> Optional[int]:
        """Return the system ID under a widget-local coordinate.

        Args:
            child_pos: Position in this widget's coordinate space.

        Returns:
            System ID under the cursor, or None.
        """
        if not self.systems:
            return None
        if isinstance(child_pos, (QtCore.QPointF, QtCore.QPoint)):
            mouse_x = float(child_pos.x())
            mouse_y = float(child_pos.y())
        else:
            mouse_x, mouse_y = child_pos
        width = self.width()
        height = self.height()
        if width <= 0 or height <= 0:
            return None
        if mouse_x < 0.0 or mouse_y < 0.0 or mouse_x >= width or mouse_y >= height:
            return None
        hovered_id = None
        if self._gpu_picking_enabled:
            hovered_id = self._gpu_pick_system_id(mouse_x, mouse_y, width, height)
        if hovered_id is not None:
            return hovered_id
        return self._cpu_pick_system_id(mouse_x, mouse_y, width, height)

    def set_line_thickness(self, thickness: float) -> None:
        """Update screen-space line thickness and trigger a repaint.

        Args:
            thickness: Line thickness in pixels.

        Returns:
            None.
        """
        self.line_thickness = max(0.1, float(thickness))

    def _focus_on_system(self, system: System) -> None:
        """Recenter orbit controls and camera target on a specific system.

        Args:
            system: Target system to focus.

        Returns:
            None.
        """
        if self.mouse_3d:
            self.target[0] = float(system.x)
            self.target[1] = float(system.y)
            self.camera_target[0] = float(system.x)
            self.camera_target[1] = float(system.y)
            self.camera_target[2] = float(system.z)
        else:
            self.target[0] = -float(system.x)
            self.target[1] = -float(system.y)



    def set_mouse_mode_3d(self, enabled: bool) -> None:
        """Toggle orbit-style mouse interactions.

        Args:
            enabled: Whether 3D orbit controls are enabled.

        Returns:
            None.
        """
        self.mouse_3d = bool(enabled)
        self.orbiting = False
        self.panning = False
        self.unsetCursor()

    @PySide6.QtCore.Slot(int)
    def set_system_marked(self, system_id: int) -> None:
        """Set the mark timer for a system to 5000 ms.

        Args:
            system_id: Target system ID.

        Returns:
            None.
        """
        system_idx = self.system_index_by_id.get(int(system_id))
        if system_idx is None:
            return
        self.mark_timers[system_idx] = self.systems[system_idx].marker
        self._system_rebuild_pending = True

    @PySide6.QtCore.Slot(int)
    def set_system_killed(self, system_id: int) -> None:
        """Set the kill timer for a system to 5000 ms.

        Args:
            system_id: Target system ID.

        Returns:
            None.
        """
        system_idx = self.system_index_by_id.get(int(system_id))
        if system_idx is None:
            return
        self.systems[system_idx].killed = 5000
        self.kill_timers[system_idx] = 5000.0
        self._system_rebuild_pending = True

    @PySide6.QtCore.Slot(int, int, float)
    def set_system_intel_status(self, system_id: int, status: int, status_time: float) -> None:
        """Update the intel status and timestamp for a system.

        Args:
            system_id: Target system ID.
            status: Intel status enum value.
            status_time: Timestamp for the intel entry.

        Returns:
            None.
        """
        system_idx = self.system_index_by_id.get(int(system_id))
        if system_idx is None:
            return
        try:
            intel_status = IntelStatus(int(status))
        except ValueError:
            intel_status = IntelStatus.NONE
        if intel_status == IntelStatus.NONE:
            status_time = 0.0
        elif status_time <= 0.0:
            status_time = time.time()
        elif status_time < self.intel_time_base:
            self.intel_time_base = float(status_time)
        self.systems[system_idx].intel_status = intel_status
        self.systems[system_idx].intel_status_time = float(status_time)
        if not self._intel_status_active and self._show_intel_minutes:
            self._show_intel_minutes = False
        self._system_rebuild_pending = True
        self._text_rebuild_pending = True

    @PySide6.QtCore.Slot(int,bool)
    def centerMapOnId(self, system_id: int, animate:bool=False) -> None:
        """Center the map view on the system with the provided ID.

        Args:
            system_id: Target system or region ID.

        Returns:
            None.
        """
        system_idx = self.system_index_by_id.get(int(system_id))
        if system_idx is None:
            return
        system = self.systems[system_idx]
        if self.mouse_3d:
            self._focus_on_system(system)
        else:
            self.target[0] = -float(system.x)
            self.target[1] = -float(system.y)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        """Start panning when the left mouse button is pressed.

        Args:
            event: Qt mouse event.

        Returns:
            None.
        """
        self._last_mouse_pos = event.position()
        if event.button() == QtCore.Qt.MouseButton.RightButton:
            hovered_id = self.objectUnderMouse(event.position())
            if hovered_id is not None:
                self.systemRightClicked.emit(int(hovered_id))
                event.accept()
                print(" mousePressEvent Hover ID {}".format(hovered_id))
                return

        if self.mouse_3d:
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                self.orbiting = True
                self.last_pos = event.position()
                self.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)
                event.accept()
                return
            if event.button() in (
                QtCore.Qt.MouseButton.MiddleButton,
                QtCore.Qt.MouseButton.RightButton,
            ):
                self.panning = True
                self.last_pos = event.position()
                self.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)
                event.accept()
                return
        else:
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                self.panning = True
                self.last_pos = event.position()
                self.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)
                event.accept()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        """Stop panning when the left mouse button is released.

        Args:
            event: Qt mouse event.

        Returns:
            None.
        """
        self._last_mouse_pos = event.position()
        if self.mouse_3d:
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                self.orbiting = False
            if event.button() in (
                QtCore.Qt.MouseButton.MiddleButton,
                QtCore.Qt.MouseButton.RightButton,
            ):
                self.panning = False
            if not self.orbiting and not self.panning:
                self.unsetCursor()
            event.accept()
            return
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.panning = False
            self.unsetCursor()
            event.accept()

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        """Emit the double-clicked system ID and optionally recenter in 3D mode.

        Args:
            event: Qt mouse event.

        Returns:
            None.
        """
        if event.button() != QtCore.Qt.MouseButton.LeftButton:
            event.ignore()

            return
        hovered_id = self.objectUnderMouse(event.position())
        if hovered_id is None:
            event.ignore()
            return
        hovered = self._system_by_id(hovered_id)
        self.set_system_marked(hovered_id)
        self.set_system_intel_status(hovered_id, IntelStatus.GREEN, time.time())
        self.systemDoubleClicked.emit(int(hovered_id))
        if self.mouse_3d:
            self.orbiting = False
            self.panning = False
            if hovered is not None:
                self._focus_on_system(hovered)
            self.unsetCursor()
        event.accept()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        """Pan the view by dragging and report hover changes.

        Args:
            event: Qt mouse event.

        Returns:
            None.
        """
        pos = event.position()
        self._last_mouse_pos = pos
        width = max(self.width(), 1)
        height = max(self.height(), 1)

        if self.mouse_3d:
            orbit_dir = -1.0
            if self.orbiting:
                delta = pos - self.last_pos
                self.orbit_yaw += float(delta.x() * orbit_dir) * 0.005
                self.orbit_pitch = float(
                    np.clip(self.orbit_pitch - float(delta.y() * orbit_dir) * 0.005, -1.3, 1.3)
                )
                self.last_pos = pos
                event.accept()
                return
            if self.panning:
                aspect = width / height
                effective_zoom = max(self.base_zoom / max(self.camera_distance, 1e-3), 1e-3)
                span = self.base_span / effective_zoom
                world_per_px_x = (span * aspect * 2.0) / width
                world_per_px_y = (span * 2.0) / height
                delta = pos - self.last_pos
                self.target[0] -= float(delta.x()) * world_per_px_x
                self.target[1] += float(delta.y()) * world_per_px_y
                self.camera_target[0] = self.target[0]
                self.camera_target[1] = self.target[1]
                self.last_pos = pos
                event.accept()
                return

        if self.panning:
            aspect = width / height
            span = self.base_span / self.zoom
            world_per_px_x = (span * aspect * 2.0) / width
            world_per_px_y = (span * 2.0) / height
            delta = pos - self.last_pos
            self.target[0] += float(delta.x()) * world_per_px_x
            self.target[1] -= float(delta.y()) * world_per_px_y
            self.last_pos = pos
            #print("Panning {} {}".format(self.target[0],self.target[1]  ))
        event.accept()

    def leaveEvent(self, event: QtCore.QEvent) -> None:
        """Clear hover tracking when the cursor leaves the widget.

        Args:
            event: Qt leave event.

        Returns:
            None.
        """
        self._last_mouse_pos = None
        self._hovered_system = None
        event.accept()

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        """Zoom in/out with the mouse wheel.

        Args:
            event: Qt wheel event.

        Returns:
            None.
        """
        steps = float(event.angleDelta().y()) / 120.0
        if steps == 0.0:
            return

        if self.mouse_3d:
            self.camera_distance *= 1.2 ** steps
            self.camera_distance = max(0.03, min(10.0, self.camera_distance))
            self.zoom = float(self.camera_distance)
            event.accept()
            return

        width = max(self.width(), 1)
        height = max(self.height(), 1)
        aspect = width / height
        mouse_x = float(event.position().x())
        mouse_y = float(event.position().y())
        ndc_x = (mouse_x / width) * 2.0 - 1.0
        ndc_y = 1.0 - (mouse_y / height) * 2.0

        half_w = self.base_span * aspect
        half_h = self.base_span

        hovered_id = self.objectUnderMouse((mouse_x, mouse_y))
        hovered = self._system_by_id(hovered_id)
        if hovered is not None:
            anchor_x = hovered.x
            anchor_y = hovered.y
        else:
            anchor_x = ndc_x * half_w / self.zoom - self.target[0]
            anchor_y = ndc_y * half_h / self.zoom - self.target[1]

        new_zoom = self.zoom * (1.2 ** steps)
        new_zoom = max(0.1, min(400.0, new_zoom))

        self.target[0] = (ndc_x * half_w) / new_zoom - anchor_x
        self.target[1] = (ndc_y * half_h) / new_zoom - anchor_y
        self.zoom = new_zoom
        #print("Zoom {}".format(self.zoom))
        event.accept()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Release GL resources when the widget closes.

        Args:
            event: Qt close event.

        Returns:
            None.
        """
        if self.line_program:
            glDeleteProgram(self.line_program)
        if self.text_program:
            glDeleteProgram(self.text_program)
        if self.structure_program:
            glDeleteProgram(self.structure_program)
        if self.system_program:
            glDeleteProgram(self.system_program)
        if self.pick_program:
            glDeleteProgram(self.pick_program)
        if self.point_vbo:
            glDeleteBuffers(1, [self.point_vbo])
        if self.line_vbo:
            glDeleteBuffers(1, [self.line_vbo])
        if self.line_constellation_vbo:
            glDeleteBuffers(1, [self.line_constellation_vbo])
        if self.line_region_vbo:
            glDeleteBuffers(1, [self.line_region_vbo])
        if self.bridge_line_vbo:
            glDeleteBuffers(1, [self.bridge_line_vbo])
        for draw in self.structure_draws:
            if draw.get("fill_vbo"):
                glDeleteBuffers(1, [draw["fill_vbo"]])
            if draw.get("border_vbo"):
                glDeleteBuffers(1, [draw["border_vbo"]])
            if draw.get("inst_vbo"):
                glDeleteBuffers(1, [draw["inst_vbo"]])
            if draw.get("fill_vao"):
                glDeleteVertexArrays(1, [draw["fill_vao"]])
            if draw.get("border_vao"):
                glDeleteVertexArrays(1, [draw["border_vao"]])
        if self.text_vbo:
            glDeleteBuffers(1, [self.text_vbo])
        if self.text_instance_vbo:
            glDeleteBuffers(1, [self.text_instance_vbo])
        if self.text_dynamic_instance_vbo:
            glDeleteBuffers(1, [self.text_dynamic_instance_vbo])
        if self.system_ssbo:
            glDeleteBuffers(1, [self.system_ssbo])
        if self.pick_positions_ssbo:
            glDeleteBuffers(1, [self.pick_positions_ssbo])
        if self.pick_distances_ssbo:
            glDeleteBuffers(1, [self.pick_distances_ssbo])
        if self.system_vao:
            glDeleteVertexArrays(1, [self.system_vao])
        super().closeEvent(event)


def main() -> None:
    """Application entry point.

    Returns:
        None.
    """
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.ApplicationAttribute.AA_UseDesktopOpenGL)
    fmt = QtGui.QSurfaceFormat()
    fmt.setRenderableType(QtGui.QSurfaceFormat.RenderableType.OpenGL)
    fmt.setVersion(4, 6)
    fmt.setProfile(QtGui.QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    fmt.setDepthBufferSize(24)
    fmt.setSamples(4)
    fmt.setSwapInterval(1)  # sync buffer swaps to the display refresh when supported
    QtGui.QSurfaceFormat.setDefaultFormat(fmt)
    app = QtWidgets.QApplication([])

    systems = []
    info_path = os.path.join(os.path.dirname(__file__), "InfoObjects.txt")
    data_path = os.path.join(os.path.dirname(__file__), "mapSolarSystems.jsonl")
    use_mouse_3d = False
    if os.path.exists(data_path):
        try:
            systems = load_systems(data_path, info_objects_path=info_path,mouse_3d=use_mouse_3d)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Failed to load {data_path}: {exc}")

    if not systems:
        systems = create_default_systems()

    chars = collect_name_chars(systems)
    atlas_dir = os.path.join(os.path.dirname(__file__), "atlas")
    font_family = select_font_family(["Noto Sans CJK", "Noto Sans"])
    _, atlas_json = generate_font_atlas(atlas_dir, font_family, 24, chars, logical_font_size=8)
    stargates_path = os.path.join(os.path.dirname(__file__), "mapStargates.jsonl")
    line_vertices: np.ndarray | ConnectionLineGroups = np.array([], dtype=np.float32)
    if os.path.exists(stargates_path):
        try:
            line_vertices = load_connections(stargates_path, systems, grouped=True)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Failed to load {stargates_path}: {exc}")
    if not line_vertices.size:
        print("No stargate connections loaded.")

    jb_path = os.path.join(os.path.dirname(__file__), "jb.txt")
    jump_bridge_vertices = np.array([], dtype=np.float32)
    if os.path.exists(jb_path):
        try:
            jump_bridge_vertices = load_jump_bridges(jb_path, systems)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Failed to load {jb_path}: {exc}")
    if not jump_bridge_vertices.size:
        print("No jump bridge connections loaded.")

    window = QtWidgets.QMainWindow()
    window.setWindowTitle("Universe Star Map")
    widget = StarMapWidget(
        systems,
        atlas_json,
        line_vertices,
        jump_bridge_vertices,
        mouse_3d=use_mouse_3d,
    )
    widget.setFormat(fmt)
    window.setCentralWidget(widget)
    window.resize(1024, 768)
    widget.centerMapOnId(30001967)
    widget.centerMapOnId(30002488)

    window.show()
    app.exec()


if __name__ == "__main__":
    main()
# codex resume 019c2992-06a8-7a41-9195-a85f05f9e704
