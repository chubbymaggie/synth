/*
 * Name:           loop4
 * Linear-program: true
 * Linear-rank:    true
 * Conditional:    false
 * Float:          false
 * Bitvector:      false
 * Lexicographic:  2
 * Terminates:     true
 */

int main(void) {
  int a, b, x, y;

  x = a;
  y = b;

  while (x > 0 && y > 0) {
    if (nondet() == 1) {
      x--;
      y++;
    } else {
      y--;
    }
  }
}
