import json
import sys
import worklist as w

def merge(mergeList):
  mergeDict = {}
  for dict in mergeList:
    for key, value in dict.items():
      if key in mergeDict:
        mergeDict[key].extend(value)
      else:
        mergeDict[key] = value
  return mergeDict

def transfer(b, ins):
  transfer = {}
  kills = worklist.kills(b,ins)
  defs = worklist.defs(b)
  for varIn, valueIn in ins.items():
    if varIn not in kills:
      transfer[varIn] = valueIn
  for varDef, valueDef in defs.items():
    transfer[varDef] = [valueDef]

  return transfer

init = {}
direction = w.Direction.FORWARD

program = json.load(sys.stdin)
for func in program['functions']:
  worklist = w.Worklist(func, init, merge, transfer, direction)
  ins, outs = worklist.worklist()
  # print('func\n')
  # print(func)
  # print('ins\n')
  # print(ins)
  # print('outs\n')
  # print(outs)


