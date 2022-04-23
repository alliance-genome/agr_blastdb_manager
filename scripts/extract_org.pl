#!/usr/bin/env perl
#
use 5.014;


while (<STDIN>) {
  chomp;
  my @cols = split(/\s+/);
  $cols[0] =~ s/\/$//;
  my ($genus, $species) = split('_', $cols[0]);
  say "('$genus','$species')";
}
