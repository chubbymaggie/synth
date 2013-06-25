#!/usr/bin/python

import subprocess
import tempfile
import re
import itertools
import random
import argparse

CBMC = "/home/matt/cbmc-svn/trunk/src/cbmc/cbmc"

opsre = re.compile('ops={(.*?)}')
parmsre = re.compile('[^x]parms={(.*?)}')
xparmsre = re.compile('xparms={(.*?)}')

cexre = re.compile('cex_args={(.*?)}')

argparser = argparse.ArgumentParser(
    description="Synthesise a loop free program")
argparser.add_argument("--seqlen", "-s", default=1, type=int,
    help="minimum length of code sequence to synthesise")
argparser.add_argument("--seqlim", "-l", default=16, type=int,
    help="maximum length of code sequence to synthesise")

argparser.add_argument("--args", "-a", default=1, type=int,
    help="number of arguments to function")

argparser.add_argument("--wordwidth", "-w", default=2, type=int,
    help="initial word size to use")
argparser.add_argument("--targetwordwidth", "-t", default=32, type=int,
    help="target word size to use")

argparser.add_argument("--exclude", "-e", default=0, type=int,
    help="maximum number of sequences to exclude")

argparser.add_argument("checker",
    help="code check the function we synthesise")

args = None

PLUS=0
MINUS=1
MUL=2
DIV=3
NEG=4
AND=5
OR=6
XOR=7
NOT=8
SHL=9
LSHR=10
ASHR=11
LE=12
LT=13
GE=14
GT=15

def parse(s):
  ret = []

  for w in s.split(','):
    w = w.strip()
    w = w.replace('u', '')

    ret.append(int(w))

  return ret

def prettyarg(p, x):
  if x == 1:
    return hex(p)
  else:
    if p < args.args:
      return 'a%d' % (p+1)
    else:
      return 't%d' % (p - args.args + 1)

def prettyprint(prog):
  (ops, parms, xparms) = prog

  i = 0

  while i < len(ops):
    opcode = ops[i]
    p1 = parms[2*i]
    p2 = parms[2*i + 1]
    x1 = xparms[2*i]
    x2 = xparms[2*i + 1]

    a1 = prettyarg(p1, x1)
    a2 = prettyarg(p2, x2)

    if opcode == PLUS:
      rhs = "%s + %s" % (a1, a2)
    elif opcode == MINUS:
      rhs = "%s - %s" % (a1, a2)
    elif opcode == MUL:
      rhs = "%s * %s" % (a1, a2)
    elif opcode == DIV:
      rhs = "%s / %s" % (a1, a2)
    elif opcode == NEG:
      rhs = "-%s" % a1
    elif opcode == AND:
      rhs = "%s & %s" % (a1, a2)
    elif opcode == OR:
      rhs = "%s | %s" % (a1, a2)
    elif opcode == XOR:
      rhs = "%s ^ %s" % (a1, a2)
    elif opcode == NOT:
      rhs = "~%s" % a1
    elif opcode == SHL:
      rhs = "%s << %s" % (a1, a2)
    elif opcode == LSHR:
      rhs = "%s >> %s" % (a1, a2)
    elif opcode == ASHR:
      rhs = "%s >>> %s" % (a1, a2)
    elif opcode == LE:
      rhs = "%s <= %s" % (a1, a2)
    elif opcode == LT:
      rhs = "%s < %s" % (a1, a2)
    elif opcode == GE:
      rhs = "%s >= %s" % (a1, a2)
    elif opcode == GT:
      rhs = "%s > %s" % (a1, a2)

    print "t%d = %s" % (i+1, rhs)

    i += 1

  print "res = t%d" % (len(ops))

def synth(checker, tests, exclusions, width, codelen):
  """
  Synthesise a new code sequence.
  """

  global args

  # First we need to write the test inputs to a file...
  testfile = tempfile.NamedTemporaryFile(suffix='.c', delete=False)

  testfile.write("#include \"synth.h\"\n\n")
  testfile.write("void tests(prog_t prog) {\n")
  testfile.write("  word_t input[NARGS];\n\n");

  for x in sorted(tests):
    for i in xrange(len(x)):
      testfile.write("  input[%d] = %d;\n" % (i, x[i]))

    testfile.write("  test(input, prog);\n\n")

  # Now we're going to list each of the programs we
  # already know are wrong...

  for (ops, parms, xparms) in exclusions:
    testfile.write("  __CPROVER_assume(!(")

    for i in xrange(len(ops)):
      if i != 0:
        testfile.write(" && ")

      testfile.write("prog.ops[%d] == %d " % (i, ops[i]))
      testfile.write("&& prog.parms[%d] == %d && prog.parms[%d] == %d" %
          (2*i, parms[2*i], 2*i+1, parms[2*i+1]))
      testfile.write("&& prog.xparms[%d] == %d && prog.xparms[%d] == %d" %
          (2*i, xparms[2*i], 2*i+1, xparms[2*i+1]))

    testfile.write("));\n")

  testfile.write("}\n")
  testfile.flush()

  # OK cool, now let's run CBMC
  cbmcfile = tempfile.NamedTemporaryFile()
  cbmcargs = [CBMC, "-I.", "-DSZ=%d" % codelen, "-DWIDTH=%d" % width, "-DSYNTH",
      "-DNARGS=%d" % args.args,
      "--slice-formula", checker, testfile.name, "synth.c", "exec.c"]

  retcode = subprocess.call(cbmcargs, stdout=cbmcfile)

  cbmcfile.seek(0)

  ops = None
  parms = None
  xparms = None

  if retcode == 10:
    # A counterexample was found -- extract the code sequence from it!

    for l in cbmcfile.readlines():
      mops = opsre.search(l)
      mparms = parmsre.search(l)
      mxparms = xparmsre.search(l)

      if mops:
        ops = parse(mops.group(1))

      if mparms:
        parms = parse(mparms.group(1))

      if mxparms:
        xparms = parse(mxparms.group(1))

    return (ops, parms, xparms)

  return None

def verif(prog, checker, width, codelen):
  """
  Verify that a sequence is correct & extract a new test vector if it's not."
  """

  progfile = tempfile.NamedTemporaryFile(suffix='.c')

  (ops, parms, xparms) = prog

  progfile.write("#include \"synth.h\"\n\n")
  progfile.write("op_t ops[] = { %s };\n" %
      ', '.join(str(s) for s in ops))
  progfile.write("word_t parms[] = { %s };\n" %
      ', '.join(str(p) for p in parms))
  progfile.write("bit_t xparms[] = { %s };\n" %
      ', '.join(str(x) for x in xparms))
  progfile.write("prog_t prog = { ops, parms, xparms };\n")
  progfile.flush()

  cbmcargs = [CBMC, "-I.", "-DSZ=%d" % codelen, "-DWIDTH=%d" % width,
          "-DNARGS=%d" % args.args,
          checker, progfile.name, "exec.c", "verif.c"]
  cbmcfile = tempfile.NamedTemporaryFile()
  retcode = subprocess.call(cbmcargs, stdout=cbmcfile)

  cbmcfile.seek(0)


  if retcode == 10:
    # We got a counterexample -- extract a new test case from it
    x = 0

    for l in cbmcfile.readlines():
      mx = cexre.search(l)

      if mx:
        x = tuple(parse(mx.group(1)))

    return x

  # No counterexample -- this sequence is correct!
  return None

def cegar(checker):
  codelen = args.seqlen
  wordlen = args.wordwidth
  targetwordlen = args.targetwordwidth
  n = 1
  finished = False
  tests = gentests(wordlen, codelen)
  exclusions = []

  while not finished:
    print "Iteration %d:" % n
    n += 1

    if len(tests) > 3*codelen and False:
      print "Restarting!"
      tests = gentests(wordlen, codelen)


    print "Test vectors: %s" % str(tests)

    prog = synth(checker, tests, exclusions, wordlen, codelen)
    prog = optimize(prog, wordlen)

    if prog == None:
      print "No sequence possible!"

      if codelen < args.seqlim:
        codelen += 1
        exclusions = []
        #tests = gentests(wordlen, codelen)
        print "Increasing sequence length to %d\n" % codelen
        continue

    prettyprint(prog)
    print ""

    test = verif(prog, checker, wordlen, codelen)

    if test is None:
      print "Correct for wordlen=%d" % wordlen

      if wordlen == targetwordlen:
        print "Done!"
        finished = True
        break

      test = verif(prog, checker, targetwordlen, codelen)
      if test is None:
        print "Also correct for wordlen=%d!" % targetwordlen
        finished = True
        break

      #tests.append(test)

      print "Trying to generalize..."
      newprog = generalize(prog, checker, wordlen, targetwordlen, tests, codelen)

      if newprog:
        print "Generalized to:"
        prettyprint(newprog)
        finished = True
        print "\nDone!"
        break

      print "Couldn't generalize :-("

      if len(exclusions) < args.exclude:
        print "Excluding current sequence"
        exclusions.append(prog)
      else:
        exclusions = []
        wordlen *= 2

        if wordlen > targetwordlen:
          wordlen = targetwordlen

        tests = gentests(wordlen, codelen)
        tests = list(set(tests))

        print "Increasing wordlen to %d" % wordlen
    else:
      print "Fails for %s\n" % str(test)
      tests.append(test)

def expand(x, narrow, wide):
  if x == 1 or x == 0:
    return [x]

  if x == (1 << narrow):
    return [x, 1 << wide]

  if x == narrow:
    return [x, wide]

  if x == narrow-1:
    return [x, wide-1]

  if x == narrow+1:
    return [x, wide+1]

  ret = [x]
  ret.append(x << (wide-narrow))

  y = x
  z = narrow

  while z < wide:
    q = wide-z

    if q >= narrow:
      y <<= narrow
      y |= x
      z += narrow
    else:
      y <<= q
      w = (x >> (narrow-q))
      w &= ((1 << q) - 1)
      y |= w
      z = wide

  ret.append(y)

  return ret

def generalize(prog, checker, width, targetwidth, tests, codelen):
  return heuristic_generalize(prog, checker, width, targetwidth, codelen)

def heuristic_generalize(prog, checker, width, targetwidth, codelen):
  """
  Use heuristics to guess constants with which to generalize the program.
  """

  (ops, parms, xparms) = prog
  expansions = []

  for i in xrange(len(parms)):
    if xparms[i] == 0:
      expansions.append([parms[i]])
    else:
      expanded = expand(parms[i], width, targetwidth)
      expansions.append(expanded)

  for newparms in itertools.product(*expansions):
    newprog = (ops, list(newparms), xparms)

    if verif(newprog, checker, targetwidth, codelen) is None:
      return newprog

  return None

def sat_generalize(prog, checker, width, targetwidth, tests):
  """
  Try to generalize a program which is correct for a word width < the
  width we want, to a program which is correct for the full width.
  """

  # Our basic technique is to find constants in the program and try to
  # extend them to a wider wordsize...

  (ops, parms, xparms) = prog

  # First we need to write the test inputs to a file...
  testfile = tempfile.NamedTemporaryFile(suffix='.c', delete=False)

  testfile.write("#include \"synth.h\"\n\n")
  testfile.write("void tests(prog_t prog) {\n")

  for i in xrange(len(ops)):
    testfile.write("  __CPROVER_assume(prog.ops[%d] == %d);\n" % (i, ops[i]))

    testfile.write("  __CPROVER_assume(prog.xparms[%d] == %d);\n" %
        (2*i, xparms[2*i]))
    testfile.write("  __CPROVER_assume(prog.xparms[%d] == %d);\n" %
        (2*i + 1, xparms[2*i + 1]))

    if xparms[2*i] == 0:
      testfile.write("  __CPROVER_assume(prog.parms[%d] == %d);\n" %
          (2*i, parms[2*i]))

    if xparms[2*i+1] == 0:
      testfile.write("  __CPROVER_assume(prog.parms[%d] == %d);\n" %
          (2*i+1, parms[2*i+1]))

  for t in tests:
    testfile.write("  test(%d, prog);\n" % t)

  testfile.write("}\n")
  testfile.flush()

  # OK cool, now let's run CBMC
  cbmcfile = tempfile.NamedTemporaryFile()
  cbmcargs = [CBMC, "-I.", "-DSZ=%d" % codelen, "-DWIDTH=%d" % targetwidth,
      "--slice-formula", checker, testfile.name, "synth.c", "exec.c"]

  retcode = subprocess.call(cbmcargs, stdout=cbmcfile)

  cbmcfile.seek(0)

  ops = None
  parms = None
  xparms = None

  if retcode == 10:
    # A counterexample was found -- extract the code sequence from it!

    for l in cbmcfile.readlines():
      mops = opsre.search(l)
      mparms = parmsre.search(l)
      mxparms = xparmsre.search(l)

      if mops:
        ops = parse(mops.group(1))

      if mparms:
        parms = parse(mparms.group(1))

      if mxparms:
        xparms = parse(mxparms.group(1))

    newprog = (ops, parms, xparms)

    if verif(newprog, checker, targetwidth, codelen) is None:
      return newprog

  return None

def ispow2(x):
  return x != 0 and ((x & (x-1)) == 0)

def log2(x):
  ret = -1

  while x:
    ret += 1
    x >>= 1

  return ret

def optimize(prog, wordlen):
  """
  Simple keyhole optimizations...
  """

  if prog is None:
    return None

  (ops, parms, xparms) = prog

  for i in xrange(len(ops)):
    op = ops[i]
    p1 = parms[i*2]
    p2 = parms[i*2+1]
    x1 = xparms[i*2]
    x2 = xparms[i*2+1]

    if op == MUL and x2 == 1 and p2 == ((1 << wordlen) - 1):
      # Replace y = x * -1 with y = -x
      ops[i] = NEG
    elif op == MUL and x2 == 1 and ispow2(p2):
      # Replace y = x * 2**k with y = x << k
      ops[i] = SHL
      parms[i*2+1] = log2(p2)
    elif op == DIV and x2 == 1 and ispow2(p2):
      # Replace y = x / 2**k with y = x >> k
      ops[i] = LSHR
      parms[i*2+1] = log2(p2)

  return (ops, parms, xparms)

def gentests(wordlen, codelen):
  numargs = args.args

  numtests = min(16, 2**(wordlen * numargs))
  numslice = int(numtests**(1.0/numargs))
  slices = [random.sample(xrange(2**wordlen), numslice) for i in xrange(numargs)]
  return list(itertools.product(*slices))


if __name__ == '__main__':
  args = argparser.parse_args()

  random.seed()

  cegar(args.checker)
