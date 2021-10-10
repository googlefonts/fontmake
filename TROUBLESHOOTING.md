# Troubleshooting

Sometimes things go wrong with `fontmake`, and you will need to track down what happened. In such circumstances, it is best to remember that `fontmake` itself does not actually do very much; its job is merely to orchestrate calls to different Python libraries which perform the compilation steps. So:

* If something goes wrong with converting Glyphs files to `.designspace` and `.ufo` files, that's probably a problem with [`glyphsLib`](https://github.com/googlefonts/glyphsLib).
* Run pre-processing filters:
  * If something goes wrong converting cubics to quadratics, that's probably a problem with [`cu2qu`](https://github.com/googlefonts/cu2qu).
  * If something goes wrong when decomposing mixed glyphs, that's probably a problem with [`ufo2ft.filters.decomposeComponents`](https://github.com/googlefonts/ufo2ft/blob/main/Lib/ufo2ft/filters/decomposeComponents.py).
  * If something goes wrong when removing overlaps, that's probably a problem with [`booleanOperations`](https://github.com/typemytype/booleanOperations)
* Anything else that goes wrong is probably a problem with [`ufo2ft`](https://github.com/googlefonts/ufo2ft), except...
* ...if something goes wrong when compiling multiple files into a variable font, that's probably a problem with [`fontTools.varLib`](https://github.com/fonttools/fonttools/tree/main/Lib/fontTools/varLib).

In other words, any problems you experience are generally *not* problems with `fontmake`. But it's important to know at which point things went wrong, and which Python library was handling your font at the time.

To do this, you can follow the following troubleshooting steps: 

## Troubleshooting steps

* If your design source is a Glyphs file, the first step that `fontmake` will peform is to using `glyphsLib` to convert the file to masters + designspace and place them in the `master_ufo` directory. So a good start is to inspect the files in this directory and make sure that they look the way you would expect them to look. Pay particular attention to the axis ranges of multiple-axis fonts and the positions of masters and instances on these axes in the `.designspace` file. If this is correct, you can use `fontmake -m` on the `.designspace` file to skip the Glyphs conversion step on subsequent runs.

*  Once you have UFO files (or if you started with them in the first place), it can be helpful to pass the `--validate-ufo` flag to `fontmake` to check that the UFO files are valid and correct.

*  Next, if you receive an error from `fontmake`, you can get the full traceback by changing the log level by passing the `--verbose DEBUG` flag. Please pass this flag before filing any issues - although often the full traceback will point you to the source of the problem!

* Finally, you can debug the operation of the feature writers by passing the `--debug-feature-file <file>` flag. This will cause `fontmake` to write out the generated feature file to a known filename, allowing you to inspect the file afterwards and check that it is as expected.

If none of these steps are helpful, please file an issue in the `fontmake` repository, or in the repository of the Python library responsible for the problem.
