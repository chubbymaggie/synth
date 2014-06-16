/*
 * Name:           SVCOMP-ChenFlurMukhopadhyay-SAS12
 * Linear-program: true
 * Linear-rank:    unk
 * Conditional:    false
 * Float:          false
 * Bitvector:      unk
 * Lexicographic:  unk
 */

/*
 * Program from Fig.1 of
 * 2012SAS - Chen,Flur,Mukhopadhyay - Termination Proofs for Linear Simple Loops
 *
 * Date: 18.12.2013
 * Author: heizmann@informatik.uni-freiburg.de
 *
 */

int main()
{
  int x, y, z;

  x = nondet();
  y = nondet();
  z = nondet();

  while (x > 0) {
    x = x + y;
    y = z;
    z = -z - 1;
  }
}