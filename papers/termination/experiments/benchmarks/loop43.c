/*
 * Name:           loop43
 * Linear-program: true
 * Linear-rank:    false
 * Conditional:    false
 * Float:          false
 * Bitvector:      false
 * Lexicographic:  ?
 * Source:         Ramsey vs. Lexicographic Termination Proving, TACAS'13
 */

int main(void) {
  int x;

  while (x != 0) {
    if (x > 0)
      x--;
    else
      x++;
  }
}
