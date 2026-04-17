-- docx-polish.lua
-- Pandoc Lua filter for polished DOCX output.
--
-- Features:
--   1. Code blocks: light gray background (#F6F6F6) with amber left border
--   2. Inline code: light gray character shading
--   3. Nested list indentation is handled by the post-processing pipeline
--      (not by the active filters returned from this file)
--
-- Usage:
--   pandoc input.md -o output.docx \
--     --reference-doc=reference.docx \
--     --lua-filter=docx-polish.lua

-- Only apply to docx output
if not FORMAT:match("docx") then
  return {}
end

-- ============================================================
-- Configuration
-- ============================================================

local CODE_BG       = "F6F6F6"   -- light gray background
local CODE_BORDER   = "C8510A"   -- amber/orange left border
local CODE_FONT     = "Cascadia Code"
local CODE_SIZE     = 19         -- half-points (19 = 9.5pt)
local INLINE_CODE_BG = "F0F0F0"  -- slightly darker for inline code

-- List indentation in twips (1440 twips = 1 inch).
-- Pandoc default is ~720 twips per level. We use ~240 (~1/3).
local LIST_INDENT_PER_LEVEL = 240
local LIST_HANGING = 360  -- hanging indent for the bullet/number

-- ============================================================
-- Helpers
-- ============================================================

-- XML-escape text for embedding in OpenXML
local function escape_xml(s)
  s = s:gsub("&", "&amp;")
  s = s:gsub("<", "&lt;")
  s = s:gsub(">", "&gt;")
  s = s:gsub('"', "&quot;")
  s = s:gsub("'", "&apos;")
  return s
end

-- ============================================================
-- Code blocks → OpenXML with shading + left border
-- ============================================================

function CodeBlock(el)
  local lines = {}
  for line in (el.text .. "\n"):gmatch("(.-)\n") do
    table.insert(lines, line)
  end
  -- Remove trailing empty line if present
  if #lines > 0 and lines[#lines] == "" then
    table.remove(lines)
  end

  local xml_parts = {}
  for _, line in ipairs(lines) do
    local escaped = escape_xml(line)
    -- If line is empty, use a non-breaking space to preserve the line
    if escaped == "" then
      escaped = " "
    end
    table.insert(xml_parts, string.format(
      '<w:p>' ..
        '<w:pPr>' ..
          '<w:pStyle w:val="SourceCode"/>' ..
          '<w:shd w:val="clear" w:color="auto" w:fill="%s"/>' ..
          '<w:pBdr>' ..
            '<w:left w:val="single" w:sz="24" w:space="10" w:color="%s"/>' ..
          '</w:pBdr>' ..
          '<w:spacing w:before="0" w:after="0" w:line="280" w:lineRule="auto"/>' ..
        '</w:pPr>' ..
        '<w:r>' ..
          '<w:rPr>' ..
            '<w:rFonts w:ascii="%s" w:hAnsi="%s" w:cs="%s"/>' ..
            '<w:sz w:val="%d"/>' ..
            '<w:szCs w:val="%d"/>' ..
            '<w:shd w:val="clear" w:color="auto" w:fill="%s"/>' ..
          '</w:rPr>' ..
          '<w:t xml:space="preserve">%s</w:t>' ..
        '</w:r>' ..
      '</w:p>',
      CODE_BG, CODE_BORDER,
      CODE_FONT, CODE_FONT, CODE_FONT,
      CODE_SIZE, CODE_SIZE,
      CODE_BG,
      escaped
    ))
  end

  return pandoc.RawBlock("openxml", table.concat(xml_parts, "\n"))
end

-- ============================================================
-- Inline code → OpenXML run with character shading
-- ============================================================

function Code(el)
  local escaped = escape_xml(el.text)
  local xml = string.format(
    '<w:r>' ..
      '<w:rPr>' ..
        '<w:rFonts w:ascii="%s" w:hAnsi="%s" w:cs="%s"/>' ..
        '<w:sz w:val="%d"/>' ..
        '<w:szCs w:val="%d"/>' ..
        '<w:shd w:val="clear" w:color="auto" w:fill="%s"/>' ..
      '</w:rPr>' ..
      '<w:t xml:space="preserve">%s</w:t>' ..
    '</w:r>',
    CODE_FONT, CODE_FONT, CODE_FONT,
    CODE_SIZE, CODE_SIZE,
    INLINE_CODE_BG,
    escaped
  )
  return pandoc.RawInline("openxml", xml)
end

-- ============================================================
-- Nested lists → reduced indentation
-- ============================================================

-- Recursively process list items, tracking nesting depth
local function process_blocks(blocks, depth)
  local result = pandoc.Blocks({})
  for _, block in ipairs(blocks) do
    if block.t == "BulletList" then
      local items = process_bullet_list(block.content, depth + 1)
      result:extend(items)
    elseif block.t == "OrderedList" then
      local items = process_ordered_list(block.content, block.listAttributes, depth + 1)
      result:extend(items)
    else
      result:insert(block)
    end
  end
  return result
end

-- Process a bullet list at a given depth
function process_bullet_list(items, depth)
  local result = pandoc.Blocks({})
  local indent = depth * LIST_INDENT_PER_LEVEL
  local left = indent + LIST_HANGING

  for _, item in ipairs(items) do
    local sub_blocks = pandoc.Blocks({})
    local nested = pandoc.Blocks({})

    for _, block in ipairs(item) do
      if block.t == "BulletList" or block.t == "OrderedList" then
        local processed = process_blocks(pandoc.Blocks({block}), depth)
        nested:extend(processed)
      else
        sub_blocks:insert(block)
      end
    end

    -- Emit the main content of this item with custom indentation
    for i, block in ipairs(sub_blocks) do
      if block.t == "Para" or block.t == "Plain" then
        -- Build OpenXML paragraph with bullet and custom indent
        local inlines_xml = ""
        -- We need to let pandoc handle the inlines normally, so we wrap
        -- in a Div with custom-style to control indentation
        local xml_prefix = string.format(
          '<w:pPr>' ..
            '<w:pStyle w:val="ListBullet"/>' ..
            '<w:numPr><w:ilvl w:val="%d"/><w:numId w:val="1"/></w:numPr>' ..
            '<w:ind w:left="%d" w:hanging="%d"/>' ..
          '</w:pPr>',
          depth - 1, left, LIST_HANGING
        )
        -- Unfortunately we can't easily mix raw XML pPr with pandoc inlines,
        -- so we use a Div with custom attributes that pandoc respects
        local div = pandoc.Div(pandoc.Blocks({block}))
        div.attributes["custom-style"] = "List Bullet"
        result:insert(div)
        break
      else
        result:insert(block)
      end
    end

    result:extend(nested)
  end

  return result
end

-- Process an ordered list at a given depth
function process_ordered_list(items, listAttributes, depth)
  local result = pandoc.Blocks({})

  for _, item in ipairs(items) do
    local sub_blocks = pandoc.Blocks({})
    local nested = pandoc.Blocks({})

    for _, block in ipairs(item) do
      if block.t == "BulletList" or block.t == "OrderedList" then
        local processed = process_blocks(pandoc.Blocks({block}), depth)
        nested:extend(processed)
      else
        sub_blocks:insert(block)
      end
    end

    for _, block in ipairs(sub_blocks) do
      if block.t == "Para" or block.t == "Plain" then
        local div = pandoc.Div(pandoc.Blocks({block}))
        div.attributes["custom-style"] = "List Number"
        result:insert(div)
        break
      else
        result:insert(block)
      end
    end

    result:extend(nested)
  end

  return result
end

-- Note: The list indentation via Lua filters has limitations in DOCX output.
-- Pandoc's DOCX writer controls numbering definitions internally.
-- The Div/custom-style approach provides some control but may not achieve
-- exact 1/3 indentation in all cases. For precise control, post-processing
-- the DOCX with python-docx may be needed.
--
-- For now, we focus on the code shading which is the higher-impact fix,
-- and leave list processing to pandoc's defaults to avoid breaking list
-- rendering. The list functions above are defined but not wired into the
-- return table.

return {
  { CodeBlock = CodeBlock },
  { Code = Code },
}
