#!/bin/bash
for f in "Times New Roman" "EB Garamond" "Roboto"; do
  cat << TEX > scratch/test_f.tex
\documentclass{article}
\usepackage{fontspec}
\setmainfont{$f}
\begin{document}
Test font $f
\end{document}
TEX
  xelatex -interaction=nonstopmode -halt-on-error scratch/test_f.tex > /dev/null 2>&1
  echo "Font $f: exit code $?"
done
