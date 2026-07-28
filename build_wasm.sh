#!/bin/bash
set -e
set -x

# ============================================================
# build_wasm.sh - Builds piper-phonemize as WebAssembly
# with your custom espeak-ng-data (containing 'rutwik').
# ============================================================

# 1. Source emsdk environment
EMSDK_PATH="/c/Users/LENOVO/emsdk"

if [ ! -f "$EMSDK_PATH/emsdk_env.sh" ]; then
    echo "ERROR: emsdk not found"
    exit 1
fi

source "$EMSDK_PATH/emsdk_env.sh"

TOOLCHAIN_FILE="$EMSDK_PATH/upstream/emscripten/cmake/Modules/Platform/Emscripten.cmake"

# 2. THE CORE FIX: Find a cmake that is NOT Conda's cmake.
# Conda's cmake (inside miniconda3/lib/python3.13/site-packages) uses a
# Darwin.cmake that forcefully appends -Wl,-search_paths_first which
# wasm-ld does not understand. We must bypass it.
#
# Priority order:
#   a) Homebrew cmake: /opt/homebrew/bin/cmake or /usr/local/bin/cmake
#   b) emsdk's own bundled cmake (may not exist on all installs)
#   c) System cmake at /usr/bin/cmake (Apple-installed via Xcode)
#   d) Give up and tell the user to install cmake via Homebrew

CLEAN_CMAKE="/c/Program Files/CMake/bin/cmake"

if [ ! -x "$CLEAN_CMAKE" ]; then
    echo "ERROR: cmake not found"
    exit 1
fi

echo "cmake version: $("$CLEAN_CMAKE" --version | head -1)"

# 3. Patch Emscripten wchar.h (macOS Perl-compatible syntax)
perl -pi -e 's/(int\s+(iswalnum|iswalpha|iswblank|iswcntrl|iswgraph|iswlower|iswprint|iswpunct|iswspace|iswupper|iswxdigit)\(wint_t\))/\/\/ $1/g' \
    "$EMSDK_PATH/upstream/emscripten/cache/sysroot/include/wchar.h" || true

# 4. Clone the WASM-compatible fork of piper-phonemize
cd /c/Users/LENOVO
if [ ! -d "$HOME/piper-phonemize-wasm" ]; then
    git clone --depth 1 https://github.com/wide-video/piper-phonemize.git piper-phonemize-wasm
fi
cd piper-phonemize-wasm

# Reset CMakeLists.txt to original state before patching (prevents duplication on re-runs)
git checkout -- CMakeLists.txt

# ---------------------------------------------------------------
# CRITICAL PATCH: The CMakeLists.txt uses ExternalProject_Add to 
# build espeak-ng as a nested sub-project but does NOT pass the
# Emscripten toolchain file to that inner build. This causes the
# inner cmake to load macOS's Darwin.cmake and inject linker flags
# that wasm-ld does not understand.
#
# We patch CMakeLists.txt to pass the toolchain file through.
# ---------------------------------------------------------------
perl -i -0pe 's/(ExternalProject_Add\(\s*espeak_ng_external.*?)(CMAKE_ARGS -DCMAKE_INSTALL_PREFIX)/$1CMAKE_ARGS -DCMAKE_TOOLCHAIN_FILE:FILEPATH=\${CMAKE_TOOLCHAIN_FILE}\n        $2/s' CMakeLists.txt

# PATCH 2: The Linux branch of CMakeLists.txt adds "-Wl,-rpath,'$ORIGIN'" to CXX flags.
# Emscripten is NOT APPLE so it falls into that branch. wasm-ld does not support -rpath.
# We change "elseif(NOT APPLE)" to "elseif(NOT APPLE AND NOT EMSCRIPTEN)"
perl -i -pe "s/elseif\(NOT APPLE\)/elseif(NOT APPLE AND NOT EMSCRIPTEN)/g" CMakeLists.txt

# PATCH 3: libespeak-ng.a uses ucd_* symbols (Unicode Character Database) but
# the final link step doesn't include -lucd. We add 'ucd' to piper_phonemize_exe
# target link libraries.
perl -i -pe 's/(target_link_libraries\(piper_phonemize_exe PUBLIC\s*\n\s*piper_phonemize\s*\n\s*espeak-ng)/$1\n    ucd/g' CMakeLists.txt

echo "Patched CMakeLists.txt:"
echo "  1. Added Emscripten toolchain to inner espeak-ng ExternalProject_Add"
echo "  2. Excluded -Wl,-rpath from Emscripten build"
echo "  3. Added libucd to piper_phonemize_exe link libraries"
grep -n "TOOLCHAIN\|EMSCRIPTEN\|ucd" CMakeLists.txt

# 5. Unset ALL Conda/Mac build env vars to ensure a clean environment
unset LDFLAGS CFLAGS CXXFLAGS CPPFLAGS
unset MACOSX_DEPLOYMENT_TARGET SDKROOT CONDA_BUILD_SYSROOT
unset LD_LIBRARY_PATH DYLD_LIBRARY_PATH
export LDFLAGS="" CFLAGS="" CXXFLAGS="" CPPFLAGS=""

# 6. Set espeak-ng-data path (YOUR custom data with rutwik voice!)
ESPEAK_SOURCE_DIR="/g/DS_AI/NG/Voice_training/Indian_English/espeak-ng"

# 6.5 Convert espeak-ng-data path to Windows format for Emscripten.
# Emscripten's file_packager is a native Python script that doesn't understand
# Git Bash paths (/g/...), so we use the C:/ (Windows) format.
ESPEAK_DATA_WIN="G:/DS_AI/NG/Voice_training/Indian_English/espeak-ng/espeak-ng-data"

# 7. Build flags: split into COMPILE flags and LINKER flags.
#    The -s settings and --preload-file are LINKER-only flags.
#    Passing them as CXX_FLAGS causes em++ to treat path args as source files.
EMSCRIPTEN_LINKER_FLAGS="-O3 \
    -s INVOKE_RUN=0 \
    -s MODULARIZE=1 \
    -s EXPORT_NAME=createPiperPhonemize \
    -s EXPORTED_FUNCTIONS=[_main] \
    -s EXPORTED_RUNTIME_METHODS=[callMain,FS] \
    --preload-file ${ESPEAK_DATA_WIN}@/espeak-ng-data"

# 8. Find ninja build tool
# Ninja is required by CMake for this build. Search common locations.
NINJA_EXE=""
for candidate in \
    "$(which ninja 2>/dev/null)" \
    "/c/Users/LENOVO/AppData/Local/Programs/Python/Python311/Scripts/ninja.exe" \
    "/c/msys64/mingw64/bin/ninja.exe" \
    "/c/msys64/usr/bin/ninja.exe" \
    "/c/ProgramData/chocolatey/bin/ninja.exe" \
    "/c/Program Files/Ninja/ninja.exe"; do
    if [ -n "$candidate" ] && [ -x "$candidate" ]; then
        NINJA_EXE="$candidate"
        break
    fi
done

if [ -z "$NINJA_EXE" ]; then
    echo "ERROR: ninja not found! Install it with one of:"
    echo "  pip install ninja"
    echo "  choco install ninja"
    echo "  pacman -S mingw-w64-x86_64-ninja   (in MSYS2)"
    exit 1
fi
echo "Using ninja: $NINJA_EXE"

# 9. First cmake configure pass using CLEAN, non-Conda cmake
# We explicitly use emcmake to tell cmake to use Emscripten as the compiler
"$EMSDK_PATH/upstream/emscripten/emcmake.bat" "$CLEAN_CMAKE" -Bbuild \
    -DCMAKE_INSTALL_PREFIX=install \
    -DBUILD_TESTING=OFF \
    -G "Ninja" \
    -DCMAKE_MAKE_PROGRAM="$NINJA_EXE" \
    -DCMAKE_CXX_FLAGS="-O3" \
    -DCMAKE_EXE_LINKER_FLAGS="$EMSCRIPTEN_LINKER_FLAGS -L/c/Users/LENOVO/piper-phonemize-wasm/build/ei/lib -lucd"

# 10. First build pass — downloads sources & partially compiles. Expected to FAIL on:
#     - speechWaveGenerator.cpp (using namespace std; conflict)
#     - intonations/phonemes (tries to run WASM binary natively)
#     - symlinks (Windows requires admin)
set +e
"$EMSDK_PATH/upstream/emscripten/emmake.bat" "$NINJA_EXE" -C build
FIRST_BUILD_RC=$?
set -e
echo ""
echo "First build pass exit code: $FIRST_BUILD_RC (non-zero is expected)"
echo ""

# ============================================================
# 11. Post-first-build patches
#     The ExternalProject has now downloaded espeak-ng source into
#     build/e/src/espeak_ng_external/ and created build.ninja in
#     build/e/src/espeak_ng_external-build/. Now we can patch them.
# ============================================================

INNER_BUILD="build/e/src/espeak_ng_external-build"
INNER_SRC="build/e/src/espeak_ng_external"
INNER_NINJA="$INNER_BUILD/build.ninja"
INNER_DATA="$INNER_BUILD/espeak-ng-data"
USER_DATA="$ESPEAK_SOURCE_DIR/espeak-ng-data"

# --- [A] Fix speechWaveGenerator.cpp ---
# Emscripten's libc++ has std::sample which conflicts with espeak-ng's 'sample' typedef.
# The source was only downloaded during step 10, so we must patch it now.
SPEECH_WAVE_SRC="$INNER_SRC/src/speechPlayer/src/speechWaveGenerator.cpp"
if [ -f "$SPEECH_WAVE_SRC" ]; then
    perl -pi -e 's/using namespace std;/\/\/ using namespace std;/g' "$SPEECH_WAVE_SRC"
    echo "[A] Patched speechWaveGenerator.cpp: commented out 'using namespace std;'"
else
    echo "[A] WARNING: speechWaveGenerator.cpp not found at $SPEECH_WAVE_SRC"
fi

# --- [B] Fix data compilation: replace espeak-ng.js calls with no-ops ---
# The COMMAND lines in build.ninja contain the FULL absolute path like:
#   C:/Users/LENOVO/piper-phonemize-wasm/build/e/src/espeak_ng_external-build/src/espeak-ng.js
# We must replace the ENTIRE path (not just the tail) with 'echo', otherwise
# the shell sees "C:/.../echo SKIPPED" as a path to execute.
if [ -f "$INNER_NINJA" ]; then
    # Get the Windows-style inner build path for matching
    INNER_BUILD_ABS=$(cd "$INNER_BUILD" && pwd)
    echo "[B] Inner build abs path: $INNER_BUILD_ABS"

    # Replace full path to espeak-ng.js with just 'echo'
    # The path in build.ninja uses forward slashes
    perl -pi -e "s|\Q${INNER_BUILD_ABS}\E/src/espeak-ng\\.js|echo|g" "$INNER_NINJA"

    # Also try the C:/ style path (some entries may use it)
    INNER_BUILD_C=$(echo "$INNER_BUILD_ABS" | sed 's|^/c/|C:/|')
    perl -pi -e "s|\Q${INNER_BUILD_C}\E/src/espeak-ng\\.js|echo|g" "$INNER_NINJA"

    echo "[B] Patched build.ninja: replaced espeak-ng.js invocations with 'echo'"

    # Verify the patch worked
    if grep -q "espeak-ng\.js" "$INNER_NINJA"; then
        echo "[B] WARNING: Some espeak-ng.js references may remain. Doing broader replace..."
        perl -pi -e 's|[A-Za-z]:/[^ ]*espeak_ng_external-build/src/espeak-ng\.js|echo|g' "$INNER_NINJA"
    fi
    echo "[B] Remaining espeak-ng.js references: $(grep -c 'espeak-ng\.js' "$INNER_NINJA" 2>/dev/null || echo 0)"
fi

# --- [C] Fix symlinks: create source file so cmake -E copy works ---
# The build tries: cmake -E create_symlink espeak-ng speak-ng
# On Windows, create_symlink requires admin. We replace it with 'copy'.
# But 'copy' requires the source file 'espeak-ng' to exist.
# The WASM build produces 'espeak-ng.js', not 'espeak-ng'.
# Solution: create an empty stub file and replace create_symlink with copy.
ESPEAK_NG_JS="$INNER_BUILD/src/espeak-ng.js"
ESPEAK_NG_STUB="$INNER_BUILD/src/espeak-ng"
if [ -f "$ESPEAK_NG_JS" ]; then
    cp "$ESPEAK_NG_JS" "$ESPEAK_NG_STUB"
    echo "[C] Created espeak-ng stub from espeak-ng.js"
elif [ ! -f "$ESPEAK_NG_STUB" ]; then
    # If .js doesn't exist yet either, create an empty stub
    touch "$ESPEAK_NG_STUB"
    echo "[C] Created empty espeak-ng stub"
fi

if [ -f "$INNER_NINJA" ]; then
    perl -pi -e 's/create_symlink/copy/g' "$INNER_NINJA"
    echo "[C] Patched build.ninja: replaced create_symlink with copy"
fi

# --- [D] Copy pre-compiled espeak-ng-data files ---
# The user has pre-compiled data at ESPEAK_SOURCE_DIR. Copy it into the inner build
# so ninja considers those targets up-to-date.
echo "[D] Copying pre-compiled espeak-ng-data from user's build..."
for f in intonations phondata phondata-manifest phonindex phontab; do
    if [ -f "$USER_DATA/$f" ]; then
        cp "$USER_DATA/$f" "$INNER_DATA/$f"
        echo "  Copied $f"
    else
        echo "  WARNING: $USER_DATA/$f not found"
    fi
done

# --- [E] Copy libucd.a ---
UCD_SRC="$INNER_BUILD/src/ucd-tools/libucd.a"
if [ -f "$UCD_SRC" ]; then
    mkdir -p build/ei/lib
    cp "$UCD_SRC" build/ei/lib/libucd.a
    echo "[E] Successfully copied libucd.a into build/ei/lib/"
else
    echo "[E] WARNING: libucd.a not found yet at $UCD_SRC (will be built in second pass)"
fi

# 12. Second build pass - with all patches applied, this should succeed!
echo ""
echo "======================================================="
echo "=== Starting second (final) build pass ==="
echo "======================================================="
"$EMSDK_PATH/upstream/emscripten/emmake.bat" "$NINJA_EXE" -C build

OUTPUT_DIR="/g/DS_AI/NG/Voice_training/Voice_assistant_demo/Compiled_voices"

mkdir -p "$OUTPUT_DIR"

cp build/piper_phonemize.js "$OUTPUT_DIR/"
cp build/piper_phonemize.wasm "$OUTPUT_DIR/"
cp build/piper_phonemize.data "$OUTPUT_DIR/"

echo "Files copied to $OUTPUT_DIR"

echo ""
echo "==========================================================="
echo "BUILD COMPLETE!"
echo "Your files are ready in: $HOME/piper-phonemize-wasm/build"
echo "  - piper_phonemize.js"
echo "  - piper_phonemize.wasm"
echo "  - piper_phonemize.data  <-- Contains your rutwik voice!"
echo ""
echo "Copy these 3 files to your voice_assistant_demo/public/piper-wasm/ folder."
echo "==========================================================="
