# Track Types

```{eval-rst}
.. currentmodule:: mava_exchange

.. automodule:: mava_exchange.tracks
   :no-members:
```

## Choosing a Track Type

- Use [**ObservationSeries**](#mava_exchange.ObservationSeries) for dense
  numeric time-series sampled at regular intervals
- Use [**AnnotationSeries**](#mava_exchange.AnnotationSeries) for single-label
  interval annotations
- Use [**AnnotationListSeries**](#mava_exchange.AnnotationListSeries) for
  multi-label interval annotations

## Track Classes

```{eval-rst}
.. autoclass:: ObservationSeries
   :members: name, description, dimensions, sampling_interval
   :exclude-members: __weakref__

.. autoclass:: AnnotationSeries
   :members:
   :exclude-members: __weakref__

.. autoclass:: AnnotationListSeries
   :members:
   :exclude-members: __weakref__

.. autoclass:: DimensionSpec
   :members:
   :exclude-members: __weakref__
```
