# Reference Guide

Complete reference for the `mava-exchange` Python package.

## By Topic

- **[Writing Packages](writer)** - Create .mediapkg files
- **[Reading Packages](reader)** - Load and inspect packages
- **[Track Types](tracks)** - Define annotation tracks
- **[Validation](validate)** - Validate package structure

## By Class

```{eval-rst}
.. currentmodule:: mava_exchange

.. autosummary::
   :toctree: ../generated
   :nosignatures:

   writer.MediaPackageWriter
   reader.MediaPackageReader
   tracks.ObservationSeries
   tracks.AnnotationSeries
   tracks.AnnotationListSeries
   tracks.DimensionSpec
   validate.ValidationResult
```

## By Function

```{eval-rst}
.. currentmodule:: mava_exchange

.. autosummary::
   :toctree: ../generated
   :nosignatures:

   validate.validate_mediapkg
   cli.inspect_cmd
   cli.validate_cmd
```
