-- auto-dark.lua
-- Filtre Lua Quarto (HTML & RevealJS) pour le thème sombre adaptatif One Dark Pro :
-- 1. Injecte les scripts JS directement depuis le dossier de l'extension (sans polluer le répertoire du .qmd via format-resources)
-- 2. Génère automatiquement les images compagnes *-auto-dark.* (via R magick ou Python PIL) pour tout fichier .qmd natif
--    même sans appel préalable à auto_dark_on()
-- 3. Encode la source sombre en data-URI dans data-auto-dark-dark-source pour garantir une compatibilité totale
--    avec embed-resources: true et l'ouverture locale en file://

local ext_dir = pandoc.path.directory(PANDOC_SCRIPT_FILE):gsub("\\", "/")

local function read_file(path)
  local f = io.open(path, "rb")
  if not f then return nil end
  local content = f:read("*all")
  f:close()
  return content
end

local function file_exists(path)
  local f = io.open(path, "rb")
  if f then
    f:close()
    return true
  end
  return false
end

local b64chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"

local function base64_encode(data)
  if not data then return "" end
  local out = {}
  local len = #data
  local i = 1
  while i <= len - 2 do
    local b1, b2, b3 = data:byte(i, i + 2)
    local n = b1 * 65536 + b2 * 256 + b3
    local c1 = math.floor(n / 262144) % 64 + 1
    local c2 = math.floor(n / 4096) % 64 + 1
    local c3 = math.floor(n / 64) % 64 + 1
    local c4 = n % 64 + 1
    out[#out + 1] = b64chars:sub(c1, c1) .. b64chars:sub(c2, c2) .. b64chars:sub(c3, c3) .. b64chars:sub(c4, c4)
    i = i + 3
  end
  local rem = len - i + 1
  if rem == 1 then
    local b1 = data:byte(i)
    local n = b1 * 65536
    local c1 = math.floor(n / 262144) % 64 + 1
    local c2 = math.floor(n / 4096) % 64 + 1
    out[#out + 1] = b64chars:sub(c1, c1) .. b64chars:sub(c2, c2) .. "=="
  elseif rem == 2 then
    local b1, b2 = data:byte(i, i + 1)
    local n = b1 * 65536 + b2 * 256
    local c1 = math.floor(n / 262144) % 64 + 1
    local c2 = math.floor(n / 4096) % 64 + 1
    local c3 = math.floor(n / 64) % 64 + 1
    out[#out + 1] = b64chars:sub(c1, c1) .. b64chars:sub(c2, c2) .. b64chars:sub(c3, c3) .. "="
  end
  return table.concat(out)
end

local function mime_type_for_ext(ext)
  local e = (ext or ""):lower()
  if e == "png" then return "image/png" end
  if e == "jpg" or e == "jpeg" then return "image/jpeg" end
  if e == "webp" then return "image/webp" end
  if e == "svg" then return "image/svg+xml" end
  return nil
end

local function companion_path_for(src)
  local res = src:gsub("(%.[a-zA-Z0-9]+)$", "-auto-dark%1")
  return res
end

local function should_process_image(img)
  if not img or not img.src then return false end
  local src = img.src
  if src:match("^https?://") or src:match("^data:") or src:match("^//") then
    return false
  end
  if src:match("%-auto%-dark%.[a-zA-Z0-9]+$") then
    return false
  end
  if src:match("logo%-universite%-") then
    return false
  end
  if img.classes:includes("auto-dark-no-filter") or
     img.classes:includes("auto-dark-render-light") or
     img.classes:includes("auto-dark-render-dark") then
    return false
  end
  local ext = src:match("%.([a-zA-Z0-9]+)$")
  if not ext then return false end
  local el = ext:lower()
  if el ~= "png" and el ~= "jpg" and el ~= "jpeg" and el ~= "webp" then
    return false
  end
  return file_exists(src)
end

local function generate_missing_companions(paths)
  if #paths == 0 then return end

  -- 1. Essai prioritaire via Rscript + magick (identique à auto-dark-setup.R)
  local r_expr = [[
    args <- commandArgs(trailingOnly = TRUE)
    if (requireNamespace("magick", quietly = TRUE)) {
      for (p in args) {
        if (file.exists(p)) {
          tryCatch({
            img <- magick::image_read(p)
            img <- magick::image_transparent(img, color = "white", fuzz = 0.005)
            magick::image_write(img, path = p)
            dark_path <- paste0(tools::file_path_sans_ext(p), "-auto-dark.", tools::file_ext(p))
            dark_img <- magick::image_negate(img)
            dark_img <- magick::image_modulate(dark_img, brightness = 115, saturation = 115, hue = 200)
            magick::image_write(dark_img, path = dark_path)
          }, error = function(e) NULL)
        }
      }
    } else {
      quit(status = 2)
    }
  ]]

  local r_args = { "-e", r_expr }
  for _, p in ipairs(paths) do
    table.insert(r_args, p)
  end

  local ok = pcall(pandoc.pipe, "Rscript", r_args, "")
  if ok and file_exists(companion_path_for(paths[1])) then
    return
  end

  -- 2. Repli via Python 3 + Pillow / NumPy si R magick n'est pas disponible
  local py_expr = [[
import sys, os, colorsys
try:
    from PIL import Image
    import numpy as np
except Exception:
    sys.exit(2)

for p in sys.argv[1:]:
    if not os.path.exists(p):
        continue
    try:
        im = Image.open(p).convert("RGBA")
        arr = np.array(im, dtype=np.float32)
        white = (arr[:, :, 0] >= 253) & (arr[:, :, 1] >= 253) & (arr[:, :, 2] >= 253)
        arr[white, 3] = 0
        Image.fromarray(arr.astype(np.uint8), "RGBA").save(p)
        dark = arr.copy()
        mask = dark[:, :, 3] > 0
        dark[mask, :3] = 255.0 - dark[mask, :3]
        dark[mask, :3] = np.clip(dark[mask, :3] * 1.12, 0, 255)
        base, ext = os.path.splitext(p)
        Image.fromarray(dark.astype(np.uint8), "RGBA").save(base + "-auto-dark" + ext)
    except Exception:
        pass
]]

  local py_args = { "-c", py_expr }
  for _, p in ipairs(paths) do
    table.insert(py_args, p)
  end
  pcall(pandoc.pipe, "python3", py_args, "")
end

local function inject_scripts()
  if not quarto or not quarto.doc then return end

  if FORMAT:match("revealjs") then
    local init_js = read_file(ext_dir .. "/auto-dark-reveal-init.js")
    local reveal_js = read_file(ext_dir .. "/auto-dark-reveal.js")
    local render_js = read_file(ext_dir .. "/auto-dark-renderings.js")
    local nav_js = read_file(ext_dir .. "/navigation-reveal.js")

    if init_js then
      quarto.doc.include_text("in-header", "<script>\n" .. init_js .. "\n</script>")
    end
    local after_parts = {}
    if reveal_js then table.insert(after_parts, "<script>\n" .. reveal_js .. "\n</script>") end
    if render_js then table.insert(after_parts, "<script>\n" .. render_js .. "\n</script>") end
    if nav_js then table.insert(after_parts, "<script>\n" .. nav_js .. "\n</script>") end
    if #after_parts > 0 then
      quarto.doc.include_text("after-body", table.concat(after_parts, "\n"))
    end
  elseif FORMAT:match("html") then
    local sys_js = read_file(ext_dir .. "/auto-dark-system.js")
    local render_js = read_file(ext_dir .. "/auto-dark-renderings.js")

    if sys_js then
      quarto.doc.include_text("in-header", "<script>\n" .. sys_js .. "\n</script>")
    end
    if render_js then
      quarto.doc.include_text("after-body", "<script>\n" .. render_js .. "\n</script>")
    end
  end
end

function Pandoc(doc)
  if not (FORMAT:match("html") or FORMAT:match("revealjs")) then
    return doc
  end

  inject_scripts()

  local missing = {}
  local missing_set = {}

  doc:walk({
    Image = function(img)
      if should_process_image(img) then
        local comp = companion_path_for(img.src)
        if not file_exists(comp) and not missing_set[img.src] then
          missing_set[img.src] = true
          table.insert(missing, img.src)
        end
      end
    end
  })

  if #missing > 0 then
    generate_missing_companions(missing)
  end

  return doc:walk({
    Image = function(img)
      if should_process_image(img) then
        local comp = companion_path_for(img.src)
        if file_exists(comp) then
          local ext = comp:match("%.([a-zA-Z0-9]+)$")
          local mime = mime_type_for_ext(ext)
          local raw_bytes = read_file(comp)
          if mime and raw_bytes then
            img.attributes["data-auto-dark-dark-source"] = "data:" .. mime .. ";base64," .. base64_encode(raw_bytes)
            if not img.classes:includes("auto-dark-no-filter") then
              img.classes:insert("auto-dark-no-filter")
            end
            return img
          end
        end
      end
      return nil
    end
  })
end
