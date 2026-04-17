-- docx-polish.lua
-- Pandoc Lua filter for polished DOCX output.
--
-- Features:
--   1. Code blocks: light gray background (#F6F6F6) with amber left border
--   2. Inline code: light gray character shading
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

return {
  { CodeBlock = CodeBlock },
  { Code = Code },
}
