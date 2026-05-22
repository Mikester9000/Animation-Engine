/**
 * @file GameEngineCompat.hpp
 * @brief Header-only C++17 bridge — Animation Engine ↔ Game Engine for Teaching.
 *
 * =============================================================================
 * PURPOSE
 * =============================================================================
 * The Animation Engine (Python) exports .anim files — JSON packages that
 * contain a Model, Skeleton, AnimationClips, and MorphTracks.  This single
 * header lets the C++ Game Engine for Teaching:
 *
 *  1. LOAD   — parse a .anim file at runtime (uses the built-in JSON parser).
 *  2. STORE  — hold the data in plain C++ structs.
 *  3. DRIVE  — feed the animation into the ECS via AnimationComponent and
 *              SkinnedSpriteComponent, updated by AnimationSystem.
 *
 * =============================================================================
 * QUICK-START
 * =============================================================================
 *
 *  // ── In your CMakeLists.txt ──────────────────────────────────────────────
 *  // target_include_directories(game PRIVATE path/to/compat)
 *
 *  // ── In any .cpp / .hpp ──────────────────────────────────────────────────
 *  #include "GameEngineCompat.hpp"
 *
 *  // Load a .anim file
 *  AE_AnimPackage pkg = AnimLoader::Load("assets/noctis.anim");
 *
 *  // Register components and system with the World
 *  world.RegisterComponent<AnimationComponent>();
 *  world.RegisterComponent<SkinnedSpriteComponent>();
 *  auto& animSys = world.RegisterSystem<AnimationSystem,
 *                      AnimationComponent, TransformComponent>();
 *  animSys.SetWorld(world);
 *
 *  // Attach to an entity
 *  AnimationComponent ac;
 *  ac.package   = &pkg;
 *  ac.clipName  = "run_cycle";
 *  ac.loop      = true;
 *  world.AddComponent(hero, ac);
 *
 * =============================================================================
 * TEACHING NOTES
 * =============================================================================
 * - The JSON parser (~200 lines) is a hand-written recursive-descent parser —
 *   a great example of how production JSON libraries work under the hood.
 * - AnimationSystem extends SystemBase from ECS.hpp, showing how to add a
 *   new game system without touching any existing engine code.
 * - Quaternion→Euler conversion shows why angles are tricky in 3D graphics.
 *
 * =============================================================================
 * DEPENDENCIES
 * =============================================================================
 *  C++17 standard library only.  No third-party libraries required.
 *  Requires: engine/ecs/ECS.hpp (for SystemBase, EntityID, TransformComponent).
 *
 * =============================================================================
 */

#pragma once

// ---------------------------------------------------------------------------
// Standard includes
// ---------------------------------------------------------------------------
#include <algorithm>
#include <array>
#include <cassert>
#include <cctype>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

// ---------------------------------------------------------------------------
// Game Engine includes (pulled in transitively from the ECS)
// ---------------------------------------------------------------------------
#include "engine/ecs/ECS.hpp"   // SystemBase, World, TransformComponent, …

// ===========================================================================
// Section 1 — Minimal JSON parser
// ===========================================================================
//
// TEACHING NOTE — Recursive Descent Parsing
// ──────────────────────────────────────────
// A recursive-descent parser mirrors the grammar of the language directly in
// code.  Each grammar rule becomes a function:
//
//   value  → object | array | string | number | bool | null
//   object → '{' (string ':' value (',' string ':' value)*)? '}'
//   array  → '[' (value (',' value)*)? ']'
//
// The functions call each other recursively — hence the name.

namespace ae_detail {

/**
 * @class AE_JsonValue
 * @brief Variant-like JSON value node.
 *
 * Can represent a JSON null, bool, number, string, array, or object.
 * All fields are public for simplicity; use the accessor helpers to read them.
 */
class AE_JsonValue {
public:
    /// JSON value types.
    enum class Type { Null, Bool, Number, String, Array, Object };

    Type                                             type = Type::Null;
    bool                                             bVal = false;
    double                                           nVal = 0.0;
    std::string                                      sVal;
    std::vector<AE_JsonValue>                        aVal; ///< Array elements.
    std::unordered_map<std::string, AE_JsonValue>    oVal; ///< Object fields.

    // -- type checks ---------------------------------------------------------
    bool isNull()   const { return type == Type::Null;   }
    bool isBool()   const { return type == Type::Bool;   }
    bool isNumber() const { return type == Type::Number; }
    bool isString() const { return type == Type::String; }
    bool isArray()  const { return type == Type::Array;  }
    bool isObject() const { return type == Type::Object; }

    // -- access helpers ------------------------------------------------------

    /// Read as a float (asserts the node is a Number).
    float asFloat() const {
        assert(isNumber() && "JSON node is not a number");
        return static_cast<float>(nVal);
    }

    /// Read as a double.
    double asDouble() const {
        assert(isNumber() && "JSON node is not a number");
        return nVal;
    }

    /// Read as an int.
    int asInt() const {
        assert(isNumber() && "JSON node is not a number");
        return static_cast<int>(nVal);
    }

    /// Read as a bool.
    bool asBool() const {
        assert(isBool() && "JSON node is not a bool");
        return bVal;
    }

    /// Read as a string reference.
    const std::string& asString() const {
        assert(isString() && "JSON node is not a string");
        return sVal;
    }

    /// Number of elements (array) or fields (object).
    std::size_t size() const {
        if (isArray())  return aVal.size();
        if (isObject()) return oVal.size();
        return 0;
    }

    /// Check whether an object has a given key.
    bool contains(const std::string& key) const {
        return isObject() && oVal.count(key) > 0;
    }

    /// Object field access (throws std::out_of_range if missing).
    const AE_JsonValue& operator[](const std::string& key) const {
        return oVal.at(key);
    }

    /// Array element access.
    const AE_JsonValue& operator[](std::size_t idx) const {
        return aVal.at(idx);
    }

    /// Object field access with default (returns a null value if missing).
    const AE_JsonValue& get(const std::string& key,
                            const AE_JsonValue& def) const {
        auto it = oVal.find(key);
        return (it != oVal.end()) ? it->second : def;
    }
};

// ---------------------------------------------------------------------------
// Parser implementation
// ---------------------------------------------------------------------------

/**
 * @class AE_JsonParser
 * @brief Recursive-descent JSON parser producing AE_JsonValue trees.
 */
class AE_JsonParser {
public:
    explicit AE_JsonParser(const std::string& src)
        : m_src(src), m_pos(0) {}

    AE_JsonValue parse() {
        skipWs();
        AE_JsonValue val = parseValue();
        skipWs();
        return val;
    }

private:
    const std::string& m_src;
    std::size_t        m_pos;

    char peek() const {
        return (m_pos < m_src.size()) ? m_src[m_pos] : '\0';
    }
    char consume() {
        return (m_pos < m_src.size()) ? m_src[m_pos++] : '\0';
    }
    void skipWs() {
        while (m_pos < m_src.size() && std::isspace((unsigned char)m_src[m_pos]))
            ++m_pos;
    }
    void expect(char c) {
        skipWs();
        if (peek() != c) {
            throw std::runtime_error(
                std::string("JSON parse error: expected '") + c +
                "' at position " + std::to_string(m_pos));
        }
        ++m_pos;
    }

    AE_JsonValue parseValue() {
        skipWs();
        char c = peek();
        if (c == '{') return parseObject();
        if (c == '[') return parseArray();
        if (c == '"') return parseString();
        if (c == 't' || c == 'f') return parseBool();
        if (c == 'n') return parseNull();
        if (c == '-' || std::isdigit((unsigned char)c)) return parseNumber();
        throw std::runtime_error(
            std::string("JSON parse error: unexpected char '") + c +
            "' at position " + std::to_string(m_pos));
    }

    AE_JsonValue parseObject() {
        AE_JsonValue v;
        v.type = AE_JsonValue::Type::Object;
        expect('{');
        skipWs();
        if (peek() == '}') { ++m_pos; return v; }
        while (true) {
            skipWs();
            std::string key = parseString().sVal;
            expect(':');
            v.oVal[key] = parseValue();
            skipWs();
            if (peek() == '}') { ++m_pos; break; }
            expect(',');
        }
        return v;
    }

    AE_JsonValue parseArray() {
        AE_JsonValue v;
        v.type = AE_JsonValue::Type::Array;
        expect('[');
        skipWs();
        if (peek() == ']') { ++m_pos; return v; }
        while (true) {
            v.aVal.push_back(parseValue());
            skipWs();
            if (peek() == ']') { ++m_pos; break; }
            expect(',');
        }
        return v;
    }

    AE_JsonValue parseString() {
        AE_JsonValue v;
        v.type = AE_JsonValue::Type::String;
        expect('"');
        std::string s;
        while (m_pos < m_src.size()) {
            char c = m_src[m_pos++];
            if (c == '"') break;
            if (c == '\\') {
                char esc = (m_pos < m_src.size()) ? m_src[m_pos++] : '\\';
                switch (esc) {
                    case '"':  s += '"';  break;
                    case '\\': s += '\\'; break;
                    case '/':  s += '/';  break;
                    case 'n':  s += '\n'; break;
                    case 'r':  s += '\r'; break;
                    case 't':  s += '\t'; break;
                    default:   s += esc;  break;
                }
            } else {
                s += c;
            }
        }
        v.sVal = std::move(s);
        return v;
    }

    AE_JsonValue parseBool() {
        AE_JsonValue v;
        v.type = AE_JsonValue::Type::Bool;
        if (m_src.compare(m_pos, 4, "true") == 0)  { v.bVal = true;  m_pos += 4; }
        else if (m_src.compare(m_pos, 5, "false") == 0) { v.bVal = false; m_pos += 5; }
        else throw std::runtime_error("JSON parse error: expected bool");
        return v;
    }

    AE_JsonValue parseNull() {
        AE_JsonValue v;
        v.type = AE_JsonValue::Type::Null;
        if (m_src.compare(m_pos, 4, "null") != 0)
            throw std::runtime_error("JSON parse error: expected null");
        m_pos += 4;
        return v;
    }

    AE_JsonValue parseNumber() {
        AE_JsonValue v;
        v.type = AE_JsonValue::Type::Number;
        std::size_t start = m_pos;
        if (peek() == '-') ++m_pos;
        while (m_pos < m_src.size() && std::isdigit((unsigned char)m_src[m_pos])) ++m_pos;
        if (m_pos < m_src.size() && m_src[m_pos] == '.') {
            ++m_pos;
            while (m_pos < m_src.size() && std::isdigit((unsigned char)m_src[m_pos])) ++m_pos;
        }
        if (m_pos < m_src.size() && (m_src[m_pos] == 'e' || m_src[m_pos] == 'E')) {
            ++m_pos;
            if (m_pos < m_src.size() && (m_src[m_pos] == '+' || m_src[m_pos] == '-')) ++m_pos;
            while (m_pos < m_src.size() && std::isdigit((unsigned char)m_src[m_pos])) ++m_pos;
        }
        v.nVal = std::stod(m_src.substr(start, m_pos - start));
        return v;
    }
};

} // namespace ae_detail

// ===========================================================================
// Section 2 — .anim data structures
// ===========================================================================
//
// These mirror the Python Animation Engine's serialisation schema exactly:
//   AnimEngine 1.0 — JSON format
//
// TEACHING NOTE — Data vs. Logic separation
// ─────────────────────────────────────────
// These structs hold *data only*.  The AnimationSystem in Section 4 holds the
// *behaviour* that operates on this data.  Keeping them separate lets you
// easily serialise/cache the loaded package without pulling in game-logic code.

/**
 * @struct AE_Vec3
 * @brief Three-component floating-point vector.
 *
 * NOTE: uses the `AE_` prefix to avoid clashing with the Game Engine's Vec3.
 */
struct AE_Vec3 {
    float x = 0.0f, y = 0.0f, z = 0.0f;

    /// Convert to the Game Engine's Vec3 (same memory layout).
    Vec3 toEngineVec3() const { return Vec3{x, y, z}; }
};

/**
 * @struct AE_Quat
 * @brief Unit quaternion (x, y, z, w) for rotation.
 *
 * TEACHING NOTE — Quaternions for Rotation
 * ─────────────────────────────────────────
 * A quaternion q = (x, y, z, w) encodes an axis-angle rotation:
 *   w = cos(θ/2),   (x, y, z) = sin(θ/2) * axis
 * Quaternions avoid gimbal lock and compose smoothly (used in FF15 and every
 * modern AAA game).  The Game Engine for Teaching uses Euler angles internally;
 * AnimationSystem converts using quaternionToEulerDeg().
 */
struct AE_Quat {
    float x = 0.0f, y = 0.0f, z = 0.0f, w = 1.0f; // identity by default

    /**
     * @brief Convert this quaternion to Euler angles (degrees: pitch, yaw, roll).
     *
     * Uses the ZYX / yaw-pitch-roll convention matching TransformComponent.rotation.
     * TEACHING NOTE: the atan2 formulas below are the standard derivation from
     * the quaternion rotation matrix.
     */
    Vec3 toEulerDeg() const {
        // Pitch (rotation around X)
        float sinPCosY = 2.0f * (w * x + y * z);
        float cosPCosY = 1.0f - 2.0f * (x * x + y * y);
        float pitch = std::atan2(sinPCosY, cosPCosY);

        // Yaw (rotation around Y)
        float sinY = 2.0f * (w * y - z * x);
        sinY = std::max(-1.0f, std::min(1.0f, sinY)); // clamp to [-1,1]
        float yaw = std::asin(sinY);

        // Roll (rotation around Z)
        float sinRCosY = 2.0f * (w * z + x * y);
        float cosRCosY = 1.0f - 2.0f * (y * y + z * z);
        float roll = std::atan2(sinRCosY, cosRCosY);

        constexpr float RAD2DEG = 180.0f / 3.14159265358979f;
        return Vec3{pitch * RAD2DEG, yaw * RAD2DEG, roll * RAD2DEG};
    }

    /// Spherical linear interpolation between two quaternions.
    AE_Quat slerp(const AE_Quat& b, float t) const {
        float dot = x*b.x + y*b.y + z*b.z + w*b.w;
        // Ensure shortest arc
        AE_Quat bb = (dot < 0.0f) ? AE_Quat{-b.x,-b.y,-b.z,-b.w} : b;
        dot = std::fabs(dot);
        if (dot > 0.9995f) {
            // Near-identical: lerp to avoid division by zero
            AE_Quat r{x + t*(bb.x-x), y + t*(bb.y-y), z + t*(bb.z-z), w + t*(bb.w-w)};
            float len = std::sqrt(r.x*r.x+r.y*r.y+r.z*r.z+r.w*r.w);
            if (len > 1e-7f) { r.x/=len; r.y/=len; r.z/=len; r.w/=len; }
            return r;
        }
        float theta0 = std::acos(dot);
        float theta  = theta0 * t;
        float sinT0  = std::sin(theta0);
        float sinT   = std::sin(theta);
        float s0 = std::cos(theta) - dot * sinT / sinT0;
        float s1 = sinT / sinT0;
        return {s0*x + s1*bb.x, s0*y + s1*bb.y, s0*z + s1*bb.z, s0*w + s1*bb.w};
    }
};

/**
 * @struct AE_Transform
 * @brief Local TRS transform for a single bone pose.
 */
struct AE_Transform {
    AE_Vec3 translation{0,0,0};
    AE_Quat rotation;
    AE_Vec3 scale{1,1,1};
};

/**
 * @struct AE_Keyframe
 * @brief A single keyframe sample in a channel.
 *
 * value is always stored as 4 floats: [x,y,z,w] for rotations, [x,y,z,0]
 * for translations/scales, [w,0,0,0] for scalar weights.
 */
struct AE_Keyframe {
    float    time       = 0.0f;
    float    value[4]   = {0,0,0,1};  ///< Padded to 4 floats for uniform access.
    float    inTangent[4] = {0,0,0,0};
    float    outTangent[4] = {0,0,0,0};
    uint8_t  interp     = 0; ///< 0=STEP, 1=LINEAR, 2=CUBIC

    static constexpr uint8_t STEP   = 0;
    static constexpr uint8_t LINEAR = 1;
    static constexpr uint8_t CUBIC  = 2;
};

/**
 * @struct AE_Channel
 * @brief A time-sorted list of keyframes for one bone × one transform target.
 */
struct AE_Channel {
    std::string boneName;
    uint8_t     target = 0; ///< 0=TRANSLATION, 1=ROTATION, 2=SCALE, 3=WEIGHT

    static constexpr uint8_t TRANSLATION = 0;
    static constexpr uint8_t ROTATION    = 1;
    static constexpr uint8_t SCALE       = 2;
    static constexpr uint8_t WEIGHT      = 3;

    std::vector<AE_Keyframe> keyframes;

    /**
     * @brief Evaluate the channel at *time* and write the result into *out[4]*.
     *
     * Handles STEP, LINEAR, and CUBIC (Hermite) interpolation.
     * For loop support, the caller should fmod(time, clipDuration) before calling.
     */
    void evaluate(float time, float out[4]) const {
        if (keyframes.empty()) {
            // Return identity value based on target
            if (target == ROTATION) { out[0]=0; out[1]=0; out[2]=0; out[3]=1; }
            else if (target == SCALE) { out[0]=1; out[1]=1; out[2]=1; out[3]=0; }
            else { out[0]=0; out[1]=0; out[2]=0; out[3]=0; }
            return;
        }

        // Clamp to first / last keyframe
        if (time <= keyframes.front().time) {
            std::copy(keyframes.front().value, keyframes.front().value+4, out);
            return;
        }
        if (time >= keyframes.back().time) {
            std::copy(keyframes.back().value, keyframes.back().value+4, out);
            return;
        }

        // Binary search for the bracket [kf0, kf1]
        std::size_t lo = 0, hi = keyframes.size() - 1;
        while (hi - lo > 1) {
            std::size_t mid = (lo + hi) / 2;
            if (keyframes[mid].time <= time) lo = mid;
            else hi = mid;
        }
        const AE_Keyframe& kf0 = keyframes[lo];
        const AE_Keyframe& kf1 = keyframes[hi];

        float dt = kf1.time - kf0.time;
        if (dt < 1e-10f) {
            std::copy(kf0.value, kf0.value+4, out);
            return;
        }

        float t = (time - kf0.time) / dt; // normalised [0,1]

        if (kf0.interp == AE_Keyframe::STEP) {
            std::copy(kf0.value, kf0.value+4, out);
            return;
        }

        if (kf0.interp == AE_Keyframe::LINEAR) {
            for (int i = 0; i < 4; ++i)
                out[i] = kf0.value[i] + (kf1.value[i] - kf0.value[i]) * t;
            return;
        }

        // CUBIC — Hermite spline (glTF CUBICSPLINE)
        // p(t) = h00*v0 + h10*dt*T0 + h01*v1 + h11*dt*T1
        float t2 = t  * t;
        float t3 = t2 * t;
        float h00 =  2*t3 - 3*t2 + 1;
        float h10 =    t3 - 2*t2 + t;
        float h01 = -2*t3 + 3*t2;
        float h11 =    t3 -   t2;
        for (int i = 0; i < 4; ++i)
            out[i] = h00 * kf0.value[i]
                   + h10 * dt * kf0.outTangent[i]
                   + h01 * kf1.value[i]
                   + h11 * dt * kf1.inTangent[i];
    }
};

/**
 * @struct AE_AnimClip
 * @brief A named collection of channels forming one complete animation.
 */
struct AE_AnimClip {
    std::string            name;
    float                  fps      = 30.0f;
    bool                   loop     = true;
    std::vector<AE_Channel> channels;
    /// Timeline event markers embedded in this clip.
    struct Event {
        std::string name;   ///< Event identifier (e.g. "footstep_left").
        float       time;   ///< Time in seconds when the event fires.
    };
    std::vector<Event> events;

    /// Duration of the clip (longest channel end-time).
    float duration() const {
        float d = 0.0f;
        for (const auto& ch : channels)
            if (!ch.keyframes.empty())
                d = std::max(d, ch.keyframes.back().time);
        return d;
    }

    /**
     * @brief Evaluate all channels for *boneName* at *time* into *out*.
     *
     * @param boneName  Bone to query.
     * @param time      Playback time in seconds (loop wrapping applied if set).
     * @param[out] out  Resulting AE_Transform.
     */
    void evaluateBone(const std::string& boneName, float time,
                      AE_Transform& out) const {
        float t = time;
        float dur = duration();
        if (loop && dur > 1e-6f) t = std::fmod(t, dur);

        out.translation = {0,0,0};
        out.rotation    = {0,0,0,1};
        out.scale       = {1,1,1};

        for (const auto& ch : channels) {
            if (ch.boneName != boneName) continue;
            float v[4] = {};
            ch.evaluate(t, v);
            if (ch.target == AE_Channel::TRANSLATION)
                out.translation = {v[0], v[1], v[2]};
            else if (ch.target == AE_Channel::ROTATION)
                out.rotation = {v[0], v[1], v[2], v[3]};
            else if (ch.target == AE_Channel::SCALE)
                out.scale = {v[0], v[1], v[2]};
        }
    }
};

/**
 * @struct AE_Bone
 * @brief One joint in the skeleton hierarchy.
 */
struct AE_Bone {
    std::string  name;
    int32_t      index       = 0;
    int32_t      parentIndex = -1; ///< -1 = root bone
    AE_Transform localBind;        ///< Bind-pose local transform
    /// Inverse bind-pose matrix (row-major, 16 floats).
    std::array<float, 16> inverseBind = {
        1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1
    };
};

/**
 * @struct AE_Skeleton
 * @brief Hierarchical array of Bones.
 */
struct AE_Skeleton {
    std::string           name;
    std::vector<AE_Bone>  bones;

    /// Find a bone by name; returns nullptr if not found.
    const AE_Bone* findBone(const std::string& n) const {
        for (const auto& b : bones) if (b.name == n) return &b;
        return nullptr;
    }
};

/**
 * @struct AE_MorphTrack
 * @brief Time-series of float weights for one named morph target.
 */
struct AE_MorphTrack {
    std::string              morphName;
    std::vector<AE_Keyframe> keyframes;

    /// Evaluate the weight at *time* (no loop — caller wraps if needed).
    float evaluate(float time) const {
        if (keyframes.empty()) return 0.0f;
        if (time <= keyframes.front().time) return keyframes.front().value[0];
        if (time >= keyframes.back().time)  return keyframes.back().value[0];
        // Linear binary-search bracket
        std::size_t lo = 0, hi = keyframes.size() - 1;
        while (hi - lo > 1) {
            std::size_t mid = (lo + hi) / 2;
            if (keyframes[mid].time <= time) lo = mid; else hi = mid;
        }
        float dt = keyframes[hi].time - keyframes[lo].time;
        if (dt < 1e-10f) return keyframes[lo].value[0];
        float t = (time - keyframes[lo].time) / dt;
        return keyframes[lo].value[0] + (keyframes[hi].value[0] - keyframes[lo].value[0]) * t;
    }
};

/**
 * @struct AE_AnimPackage
 * @brief Top-level container — the entire contents of a .anim file.
 *
 * An AE_AnimPackage is the primary currency passed between AnimLoader and
 * AnimationComponent.  The Game Engine holds one per unique character/asset.
 */
struct AE_AnimPackage {
    std::string                name;            ///< Model name.
    AE_Skeleton                skeleton;
    std::vector<AE_AnimClip>   clips;
    std::vector<AE_MorphTrack> morphTracks;
    /// Art-direction metadata from the style profile used during generation.
    std::string styleProfile;    ///< e.g. "ff10_ps2"
    std::string visualTarget;    ///< e.g. "PlayStation 2 (PS2)"
    std::string gameplayTarget;  ///< e.g. "modern action-RPG"

    /// Find a clip by name; returns nullptr if not found.
    const AE_AnimClip* findClip(const std::string& n) const {
        for (const auto& c : clips) if (c.name == n) return &c;
        return nullptr;
    }
};

// ===========================================================================
// Section 3 — AnimLoader (reads .anim JSON → AE_AnimPackage)
// ===========================================================================

/**
 * @class AnimLoader
 * @brief Loads .anim files produced by the Animation Engine Python tool.
 *
 * TEACHING NOTE — Two-Phase Loading
 * ──────────────────────────────────
 * AnimLoader::Load(path) performs two phases:
 *  1. Parse    — converts raw JSON text into a AE_JsonValue tree (Section 1).
 *  2. Deserialise — walks the tree and fills AE_AnimPackage structs (here).
 * Separating the phases makes each easier to unit-test independently.
 *
 * Usage:
 *   AE_AnimPackage pkg = AnimLoader::Load("assets/noctis.anim");
 */
class AnimLoader {
public:
    /**
     * @brief Load a .anim file from disk and return the parsed package.
     *
     * @param path  Path to the .anim file (UTF-8 string).
     * @return      Populated AE_AnimPackage.
     * @throws std::runtime_error  if the file cannot be opened or parsed.
     */
    static AE_AnimPackage Load(const std::string& path) {
        std::ifstream ifs(path);
        if (!ifs.is_open())
            throw std::runtime_error("AnimLoader: cannot open file '" + path + "'");
        std::ostringstream ss;
        ss << ifs.rdbuf();
        return LoadFromString(ss.str());
    }

    /**
     * @brief Parse a .anim JSON string (no file I/O).
     *
     * Useful for unit-testing or loading from a memory buffer.
     */
    static AE_AnimPackage LoadFromString(const std::string& json) {
        ae_detail::AE_JsonParser parser(json);
        const ae_detail::AE_JsonValue root = parser.parse();

        // Validate header
        if (!root.contains("format") ||
            root["format"].asString() != "AnimEngine")
            throw std::runtime_error(
                "AnimLoader: not an AnimEngine .anim file "
                "(missing or wrong 'format' field)");

        const std::string ver = root.contains("version")
            ? root["version"].asString() : "0.0";
        if (ver.empty() || ver[0] != '1')
            throw std::runtime_error(
                "AnimLoader: unsupported .anim version '" + ver +
                "'; this bridge supports major version 1");

        AE_AnimPackage pkg;

        // -- model (name + skeleton) -----------------------------------------
        if (root.contains("model")) {
            const auto& m = root["model"];
            if (m.contains("name")) pkg.name = m["name"].asString();
            if (m.contains("skeleton") && !m["skeleton"].isNull())
                pkg.skeleton = parseSkeleton(m["skeleton"]);
        }

        // -- clips ------------------------------------------------------------
        if (root.contains("clips")) {
            for (std::size_t i = 0; i < root["clips"].size(); ++i)
                pkg.clips.push_back(parseClip(root["clips"][i]));
        }

        // -- morph tracks -----------------------------------------------------
        if (root.contains("morph_tracks")) {
            for (std::size_t i = 0; i < root["morph_tracks"].size(); ++i)
                pkg.morphTracks.push_back(parseMorphTrack(root["morph_tracks"][i]));
        }

        // -- style-profile metadata -------------------------------------------
        if (root.contains("metadata")) {
            const auto& md = root["metadata"];
            if (md.contains("style_profile"))  pkg.styleProfile   = md["style_profile"].asString();
            if (md.contains("visual_target"))  pkg.visualTarget   = md["visual_target"].asString();
            if (md.contains("gameplay_target")) pkg.gameplayTarget = md["gameplay_target"].asString();
        }

        return pkg;
    }

private:
    // -- Skeleton / Bone -----------------------------------------------------

    static AE_Skeleton parseSkeleton(const ae_detail::AE_JsonValue& j) {
        AE_Skeleton skel;
        if (j.contains("name")) skel.name = j["name"].asString();
        if (j.contains("bones")) {
            for (std::size_t i = 0; i < j["bones"].size(); ++i)
                skel.bones.push_back(parseBone(j["bones"][i]));
        }
        return skel;
    }

    static AE_Bone parseBone(const ae_detail::AE_JsonValue& j) {
        AE_Bone b;
        if (j.contains("name"))         b.name        = j["name"].asString();
        if (j.contains("index"))        b.index       = j["index"].asInt();
        if (j.contains("parent_index")) b.parentIndex = j["parent_index"].asInt();
        if (j.contains("local_transform"))
            b.localBind = parseTransform(j["local_transform"]);
        if (j.contains("inverse_bind") && j["inverse_bind"].isArray()) {
            const auto& arr = j["inverse_bind"];
            for (std::size_t i = 0; i < 16 && i < arr.size(); ++i)
                b.inverseBind[i] = arr[i].asFloat();
        }
        return b;
    }

    static AE_Transform parseTransform(const ae_detail::AE_JsonValue& j) {
        AE_Transform t;
        auto readV3 = [](const ae_detail::AE_JsonValue& v, AE_Vec3& out) {
            if (v.isArray() && v.size() >= 3) {
                out.x = v[0].asFloat();
                out.y = v[1].asFloat();
                out.z = v[2].asFloat();
            }
        };
        auto readQ = [](const ae_detail::AE_JsonValue& v, AE_Quat& out) {
            if (v.isArray() && v.size() >= 4) {
                out.x = v[0].asFloat();
                out.y = v[1].asFloat();
                out.z = v[2].asFloat();
                out.w = v[3].asFloat();
            }
        };
        // TEACHING NOTE — the Animation Engine serialises the translation field
        // under the key "position" (matching the Python Transform class field
        // name).  We also accept "translation" for forward compatibility with
        // any future exporter version that adopts the glTF naming convention.
        if (j.contains("position"))    readV3(j["position"],    t.translation);
        else if (j.contains("translation")) readV3(j["translation"], t.translation);
        if (j.contains("rotation"))    readQ(j["rotation"],    t.rotation);
        if (j.contains("scale"))       readV3(j["scale"],      t.scale);
        return t;
    }

    // -- Animation clips / channels / keyframes ------------------------------

    static AE_AnimClip parseClip(const ae_detail::AE_JsonValue& j) {
        AE_AnimClip c;
        if (j.contains("name")) c.name = j["name"].asString();
        if (j.contains("fps"))  c.fps  = j["fps"].asFloat();
        if (j.contains("loop")) c.loop = j["loop"].asBool();
        if (j.contains("channels")) {
            for (std::size_t i = 0; i < j["channels"].size(); ++i)
                c.channels.push_back(parseChannel(j["channels"][i]));
        }
        if (j.contains("events")) {
            for (std::size_t i = 0; i < j["events"].size(); ++i) {
                const auto& ev = j["events"][i];
                AE_AnimClip::Event e;
                if (ev.contains("name")) e.name = ev["name"].asString();
                if (ev.contains("time")) e.time = ev["time"].asFloat();
                c.events.push_back(e);
            }
        }
        return c;
    }

    static AE_Channel parseChannel(const ae_detail::AE_JsonValue& j) {
        AE_Channel ch;
        if (j.contains("bone_name")) ch.boneName = j["bone_name"].asString();
        // Map string target name → integer constant
        if (j.contains("target")) {
            const std::string& tgt = j["target"].asString();
            if      (tgt == "TRANSLATION") ch.target = AE_Channel::TRANSLATION;
            else if (tgt == "ROTATION")    ch.target = AE_Channel::ROTATION;
            else if (tgt == "SCALE")       ch.target = AE_Channel::SCALE;
            else if (tgt == "WEIGHT")      ch.target = AE_Channel::WEIGHT;
        }
        if (j.contains("keyframes")) {
            for (std::size_t i = 0; i < j["keyframes"].size(); ++i)
                ch.keyframes.push_back(parseKeyframe(j["keyframes"][i], ch.target));
        }
        return ch;
    }

    static AE_Keyframe parseKeyframe(const ae_detail::AE_JsonValue& j,
                                      uint8_t target) {
        AE_Keyframe kf;
        if (j.contains("time")) kf.time = j["time"].asFloat();

        auto fillVec = [](const ae_detail::AE_JsonValue& v,
                          float out[4], uint8_t tgt) {
            if (v.isArray()) {
                for (std::size_t i = 0; i < 4 && i < v.size(); ++i)
                    out[i] = v[i].asFloat();
                // Pad: rotation w defaults to 1 if not provided
                if (tgt == AE_Channel::ROTATION && v.size() == 3)
                    out[3] = 1.0f;
            } else if (v.isNumber()) {
                out[0] = v.asFloat();
            }
        };

        fillVec(j["value"],       kf.value,      target);
        if (j.contains("in_tangent"))
            fillVec(j["in_tangent"],  kf.inTangent,  target);
        if (j.contains("out_tangent"))
            fillVec(j["out_tangent"], kf.outTangent, target);

        if (j.contains("interp")) {
            const std::string& i = j["interp"].asString();
            if      (i == "STEP")   kf.interp = AE_Keyframe::STEP;
            else if (i == "LINEAR") kf.interp = AE_Keyframe::LINEAR;
            else if (i == "CUBIC")  kf.interp = AE_Keyframe::CUBIC;
        }
        return kf;
    }

    // -- Morph tracks --------------------------------------------------------

    static AE_MorphTrack parseMorphTrack(const ae_detail::AE_JsonValue& j) {
        AE_MorphTrack mt;
        if (j.contains("morph_name")) mt.morphName = j["morph_name"].asString();
        if (j.contains("keyframes")) {
            for (std::size_t i = 0; i < j["keyframes"].size(); ++i)
                mt.keyframes.push_back(parseKeyframe(j["keyframes"][i],
                                                     AE_Channel::WEIGHT));
        }
        return mt;
    }
};

// ===========================================================================
// Section 4 — ECS Components
// ===========================================================================
//
// TEACHING NOTE — Component Design
// ─────────────────────────────────
// ECS components are plain data structs — no virtual methods, no heavy logic.
// They are registered once with World::RegisterComponent<T>() at startup.
// AnimationSystem (Section 5) is the behaviour that reads them each frame.

/**
 * @struct AnimationComponent
 * @brief Drives skeletal animation for a single entity.
 *
 * Add this to any entity that should be animated.  Point it at an
 * AE_AnimPackage (loaded once and shared), set clipName, and let
 * AnimationSystem do the rest.
 *
 * Usage:
 *   AnimationComponent ac;
 *   ac.package  = &myPackage;
 *   ac.clipName = "idle";
 *   world.AddComponent(entity, ac);
 */
struct AnimationComponent {
    /// Pointer to the shared animation data package (NOT owned by this component).
    const AE_AnimPackage* package   = nullptr;

    /// Name of the currently active AnimationClip (must exist in package->clips).
    std::string           clipName;

    /// Playback time in seconds.
    float                 time      = 0.0f;

    /// Playback speed multiplier (1.0 = normal, 2.0 = double speed, -1.0 = reverse).
    float                 speed     = 1.0f;

    /// Whether the clip should loop (overrides clip's own loop flag if set).
    bool                  loop      = true;

    /// Set to true when the clip reaches its end (only useful for non-looping clips).
    bool                  finished  = false;

    /// Name of bone whose world position drives TransformComponent.position.
    /// Leave empty to use the animation root motion bone ("root" by convention).
    std::string           rootBone;

    /// Pending transition: next clip to blend into (empty = no transition).
    std::string           nextClip;

    /// Crossfade blend duration in seconds (0 = instant switch).
    float                 blendDuration = 0.2f;

    /// Current blend weight [0,1]: 0 = fully current, 1 = fully next.
    float                 blendWeight   = 0.0f;

    // ── Helper ───────────────────────────────────────────────────────────────

    /**
     * @brief Start a smooth transition to a new clip.
     *
     * AnimationSystem picks this up and blends over blendDuration seconds.
     *
     * @param clip      Target clip name.
     * @param duration  Crossfade time in seconds.
     */
    void transitionTo(const std::string& clip, float duration = 0.2f) {
        nextClip      = clip;
        blendDuration = duration;
        blendWeight   = 0.0f;
    }
};

/**
 * @struct SkinnedSpriteComponent
 * @brief Maps bone transforms to ASCII sprite-sheet frame indices.
 *
 * TEACHING NOTE — Bridging 3D Skeletal Animation to a 2D Terminal Renderer
 * ─────────────────────────────────────────────────────────────────────────
 * The Game Engine for Teaching uses ncurses/ASCII rendering.  There are no
 * 3D meshes visible.  SkinnedSpriteComponent bridges the two worlds:
 *
 *   • Each named "region" watches one bone.
 *   • When the bone's Y-angle exceeds a threshold, the region selects a
 *     different ASCII symbol and/or ncurses colour pair.
 *   • This lets a walk cycle change the character's ASCII appearance per
 *     direction / phase, approximating sprite animation.
 *
 * For a richer integration (actual mesh deformation), see the README for
 * linking against a future OpenGL backend.
 */
struct SkinnedSpriteComponent {
    /**
     * @struct BoneRegion
     * @brief Maps one bone's orientation to a set of visual states.
     */
    struct BoneRegion {
        std::string boneName;     ///< Which bone to watch (e.g. "spine_01").
        std::string regionLabel;  ///< User-facing label (e.g. "torso").

        /**
         * @struct Frame
         * @brief One discrete visual state for this region.
         */
        struct Frame {
            char    symbol    = '@';  ///< ASCII char for this state.
            int     colorPair = 1;    ///< ncurses color pair index.
            float   minYawDeg = -180.0f; ///< Yaw range min (inclusive).
            float   maxYawDeg =  180.0f; ///< Yaw range max (exclusive).
        };

        std::vector<Frame> frames; ///< Evaluated in order; first match wins.

        /**
         * @brief Resolve the best-matching frame given bone Euler yaw angle.
         *
         * @param yawDeg  Yaw angle in degrees from the bone's current pose.
         * @return Pointer to the first matching Frame, or nullptr.
         */
        const Frame* resolve(float yawDeg) const {
            for (const auto& f : frames)
                if (yawDeg >= f.minYawDeg && yawDeg < f.maxYawDeg) return &f;
            return frames.empty() ? nullptr : &frames.front();
        }
    };

    std::vector<BoneRegion> regions; ///< One entry per tracked bone.

    /**
     * @brief Find a region by bone name.
     */
    BoneRegion* findRegion(const std::string& bone) {
        for (auto& r : regions) if (r.boneName == bone) return &r;
        return nullptr;
    }
};

/**
 * @struct MorphWeightComponent
 * @brief Stores current morph-target weights for facial / secondary animation.
 *
 * These weights can be read by a renderer that supports morph targets, or
 * used in game logic (e.g. set dialogue expression when weight > 0.5).
 */
struct MorphWeightComponent {
    /// Map from morph name → current weight [0,1].
    std::unordered_map<std::string, float> weights;

    float get(const std::string& name, float def = 0.0f) const {
        auto it = weights.find(name);
        return (it != weights.end()) ? it->second : def;
    }
    void set(const std::string& name, float w) { weights[name] = w; }
};

// ===========================================================================
// Section 5 — AnimationSystem
// ===========================================================================
//
// TEACHING NOTE — How AnimationSystem fits into the ECS
// ───────────────────────────────────────────────────────
// AnimationSystem extends SystemBase.  Register it with the World after
// registering AnimationComponent and TransformComponent:
//
//   world.RegisterComponent<AnimationComponent>();
//   world.RegisterComponent<SkinnedSpriteComponent>();
//   world.RegisterComponent<MorphWeightComponent>();
//   auto& animSys = world.RegisterSystem<AnimationSystem,
//                       AnimationComponent, TransformComponent>();
//   animSys.SetWorld(world);
//
// Each frame, call world.Update(dt) and AnimationSystem::Update(dt) is invoked
// automatically for every entity that has both AnimationComponent and
// TransformComponent.

/**
 * @class AnimationSystem
 * @brief Advances animation playback and updates ECS components each frame.
 *
 * Per-entity work:
 *  1. Advance AnimationComponent.time by deltaTime * speed.
 *  2. Evaluate the active clip's root-bone transform and write it to
 *     TransformComponent (position, rotation as Euler degrees).
 *  3. If a crossfade transition is in progress, blend between two poses.
 *  4. If SkinnedSpriteComponent is present, update symbol/colorPair from
 *     bone yaw angle.
 *  5. If MorphWeightComponent is present, update morph weights.
 */
class AnimationSystem : public SystemBase {
public:
    /**
     * @brief Provide a reference to the World for component access.
     *
     * Must be called once after RegisterSystem<AnimationSystem>().
     */
    void SetWorld(World& w) { m_world = &w; }

    // -- SystemBase interface ------------------------------------------------

    void Init() override {}
    void Shutdown() override {}

    /**
     * @brief Advance all animated entities by *deltaTime* seconds.
     *
     * @param deltaTime  Seconds since the last frame.
     */
    void Update(float deltaTime) override {
        assert(m_world && "AnimationSystem::SetWorld() was not called");

        for (EntityID entity : GetEntities()) {
            auto* ac = m_world->TryGetComponent<AnimationComponent>(entity);
            if (!ac || !ac->package) continue;

            advanceTime(*ac, deltaTime);
            applyToTransform(entity, *ac);
            applySkinnedSprite(entity, *ac);
            applyMorphWeights(entity, *ac);
        }
    }

private:
    World* m_world = nullptr;

    // -- Playback ------------------------------------------------------------

    /// Advance time, handle looping/finished, and process crossfade.
    void advanceTime(AnimationComponent& ac, float dt) const {
        // Handle crossfade transition
        if (!ac.nextClip.empty()) {
            ac.blendWeight += dt / std::max(ac.blendDuration, 0.001f);
            if (ac.blendWeight >= 1.0f) {
                // Transition complete — switch to next clip
                ac.clipName   = ac.nextClip;
                ac.time       = 0.0f;
                ac.nextClip.clear();
                ac.blendWeight = 0.0f;
                ac.finished    = false;
            }
        }

        const AE_AnimClip* clip = ac.package->findClip(ac.clipName);
        if (!clip) return;

        float dur = clip->duration();
        ac.time += dt * ac.speed;

        if (ac.loop && dur > 1e-6f) {
            // Wrap time for looping clips
            ac.time = std::fmod(ac.time, dur);
            if (ac.time < 0.0f) ac.time += dur;
        } else {
            // Clamp and mark finished
            ac.time = std::max(0.0f, std::min(ac.time, dur));
            if (ac.time >= dur) ac.finished = true;
        }
    }

    // -- Transform application -----------------------------------------------

    /**
     * @brief Evaluate the root bone's pose and write to TransformComponent.
     *
     * The root bone drives entity position/rotation.  All other bones are
     * available via the skeleton for skinned-sprite or future 3D rendering.
     *
     * TEACHING NOTE — Root Motion
     * ───────────────────────────
     * In AAA games, "root motion" means the character's movement is extracted
     * from the root bone of the animation rather than being set by a physics/
     * input system.  This gives more authentic motion (e.g. the run speed
     * exactly matches the foot animation).
     */
    void applyToTransform(EntityID entity, const AnimationComponent& ac) const {
        auto* tc = m_world->TryGetComponent<TransformComponent>(entity);
        if (!tc) return;

        const AE_AnimClip* clip = ac.package->findClip(ac.clipName);
        if (!clip) return;

        // Determine the root bone name
        const std::string rootName = ac.rootBone.empty()
            ? (ac.package->skeleton.bones.empty()
                   ? std::string{}
                   : ac.package->skeleton.bones[0].name)
            : ac.rootBone;

        if (rootName.empty()) return;

        // Evaluate primary clip
        AE_Transform poseA;
        clip->evaluateBone(rootName, ac.time, poseA);

        AE_Transform finalPose = poseA;

        // Blend with next clip if transitioning
        if (!ac.nextClip.empty() && ac.blendWeight > 0.0f) {
            const AE_AnimClip* nextClip = ac.package->findClip(ac.nextClip);
            if (nextClip) {
                AE_Transform poseB;
                nextClip->evaluateBone(rootName, 0.0f, poseB);
                float bw = ac.blendWeight;
                finalPose.translation.x = poseA.translation.x * (1-bw) + poseB.translation.x * bw;
                finalPose.translation.y = poseA.translation.y * (1-bw) + poseB.translation.y * bw;
                finalPose.translation.z = poseA.translation.z * (1-bw) + poseB.translation.z * bw;
                finalPose.rotation = poseA.rotation.slerp(poseB.rotation, bw);
                finalPose.scale.x = poseA.scale.x * (1-bw) + poseB.scale.x * bw;
                finalPose.scale.y = poseA.scale.y * (1-bw) + poseB.scale.y * bw;
                finalPose.scale.z = poseA.scale.z * (1-bw) + poseB.scale.z * bw;
            }
        }

        // Apply to TransformComponent
        tc->position = finalPose.translation.toEngineVec3();
        tc->rotation = finalPose.rotation.toEulerDeg();
        tc->scale    = finalPose.scale.toEngineVec3();
        tc->isDirty  = true;
    }

    // -- Skinned sprite update -----------------------------------------------

    /**
     * @brief Drive ASCII symbol / colorPair based on bone yaw angles.
     *
     * Reads SkinnedSpriteComponent.regions, evaluates each region's bone
     * at the current time, picks the best matching frame, and writes the
     * result into RenderComponent.
     */
    void applySkinnedSprite(EntityID entity, const AnimationComponent& ac) const {
        auto* ssc = m_world->TryGetComponent<SkinnedSpriteComponent>(entity);
        auto* rc  = m_world->TryGetComponent<RenderComponent>(entity);
        if (!ssc || !rc) return;

        const AE_AnimClip* clip = ac.package->findClip(ac.clipName);
        if (!clip) return;

        for (const auto& region : ssc->regions) {
            AE_Transform pose;
            clip->evaluateBone(region.boneName, ac.time, pose);
            Vec3 euler = pose.rotation.toEulerDeg();
            const auto* frame = region.resolve(euler.y);
            if (frame) {
                rc->symbol    = frame->symbol;
                rc->colorPair = frame->colorPair;
            }
        }
    }

    // -- Morph weight update -------------------------------------------------

    void applyMorphWeights(EntityID entity, const AnimationComponent& ac) const {
        auto* mwc = m_world->TryGetComponent<MorphWeightComponent>(entity);
        if (!mwc) return;

        for (const auto& track : ac.package->morphTracks) {
            float t = ac.time;
            mwc->set(track.morphName, track.evaluate(t));
        }
    }
};

// ===========================================================================
// Section 6 — Convenience helpers
// ===========================================================================

/**
 * @brief Register all Animation Engine components with the World.
 *
 * Call this once at startup alongside the existing RegisterAllComponents(world)
 * call already in ECS.hpp.
 *
 * TEACHING NOTE — Registration Order
 * ────────────────────────────────────
 * Components must be registered in the same order every run to keep stable
 * ComponentIDs.  Call RegisterAnimationComponents AFTER RegisterAllComponents
 * so the game-engine component IDs stay unchanged.
 */
inline void RegisterAnimationComponents(World& world) {
    world.RegisterComponent<AnimationComponent>();
    world.RegisterComponent<SkinnedSpriteComponent>();
    world.RegisterComponent<MorphWeightComponent>();
}

/**
 * @brief Register and initialise AnimationSystem in one call.
 *
 * Returns a reference to the registered system so the caller can call
 * animSys.SetWorld(world) immediately after.
 *
 * Example:
 *   auto& animSys = SetupAnimationSystem(world);
 *   animSys.SetWorld(world);  // required before first Update()
 */
inline AnimationSystem& SetupAnimationSystem(World& world) {
    auto& sys = world.RegisterSystem<AnimationSystem,
                                     AnimationComponent,
                                     TransformComponent>();
    return sys;
}
