# Displays a name and an email address by using a companion JavaScript function
# (renderString) so that they're not as easily scraped
def RenderNameAddress(name, address, tag_name="span"):
  js = "<script>"
  js += "document.write('<%s title=\"');\n" % tag_name
  js += _GetRenderStringCall(address)
  js += "document.write('\">');\n"
  js += _GetRenderStringCall(name)  
  js += "document.write('</%s>');\n" % tag_name
  js += "</script>"
  
  return js
  
  return '<%s title="%s">%s</%s>' % (tag_name, address, name, tag_name)

def _GetRenderStringCall(value):
  return "renderString(%s);\n" % (
      ",".join([str(ord(c)) for c in unicode(value)]))
