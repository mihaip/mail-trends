class StringScanner(object):
  def __init__(self, string_chunks):
    # TODO(mihaip) switch to reading from the chunks array directly to avoid 
    # extra string copies
    def flatten(chunks):
      if type(chunks) == str:
        return chunks
      else:
        chunk_strings = []
        for chunk in chunks:
          chunk_strings.append(flatten(chunk))
        return "".join(chunk_strings)
    
    self.__data = flatten(string_chunks)
    self.__index = 0
    self.__length = len(self.__data)
    
  def Peek(self):
    if self.__index >= self.__length: return None
    return self.__data[self.__index]
  
  def ReadChar(self):
    if self.__index >= self.__length: return None    
    c = self.__data[self.__index]
    self.__index += 1
    return c
    
  def ReadUntil(self, c):
    start = self.__index
    end = self.__data.find(c, self.__index)
    if end != -1:
      self.__index = end
      return self.__data[start:end]
    else:
      return ""
  
  def ConsumeAll(self, c):
    while self.__index < self.__length and self.__data[self.__index] == c:
      self.__index += 1
    
  def ConsumeChar(self, c):
    assert c == self.__data[self.__index]
    self.__index += 1
    
  def ReadUntilLength(self, length):
    ret = self.__data[self.__index:self.__index + length]
    self.__index += length
    return ret
   
  def ConsumeValue(self):
    value = None
    
    # Literal string
    if self.Peek() == "{":
      self.ConsumeChar("{")
      literal_length = int(self.ReadUntil("}"))
      self.ConsumeChar("}")
      
      value = self.ReadUntilLength(literal_length)
      
    # Quoted string 
    elif self.Peek() == "\"":
      # TODO(mihaip): can quotes be escaped inside?
      self.ConsumeChar("\"")
      value = self.ReadUntil("\"")
      self.ConsumeChar("\"")
    # Parenthesized list 
    elif self.Peek() == "(":
      self.ConsumeChar("(")
      value = []
      parenthesis_depth = 1
      
      while parenthesis_depth > 0:
        c = self.ReadChar()
        if c == "(": parenthesis_depth += 1
        if c == ")": parenthesis_depth -= 1
        
        if parenthesis_depth > 0:
          value.append(c)
      
      value = "".join(value).split()
    # Numbers
    else:
      value = self.ReadUntil(" ")
    
    return value