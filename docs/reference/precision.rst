Precision & Quantization Reference
===================================

The Babylon simulation uses quantized floating-point values to prevent
drift accumulation over long simulations. This reference documents the
Gatekeeper Pattern and quantization utilities.

.. contents:: On this page
   :local:
   :depth: 2

The Gatekeeper Pattern
----------------------

Quantization is applied at the **TYPE level** (when values enter Pydantic
models), not inside formula calculations. This ensures:

1. All values entering the simulation are on a fixed grid
2. Formula internals remain pure mathematical operations
3. No hidden precision loss during calculations

**Key Principle**: Constrained types (:class:`Probability`, :class:`Currency`,
:class:`Intensity`) apply quantization via Pydantic validators, not formulas.

Epoch 0 Physics Hardening
-------------------------

All floating-point values in the simulation snap to a precision grid:

- **Default Grid**: :math:`10^{-5}` (0.00001 resolution)
- **Purpose**: Prevent drift accumulation over long simulations
- **Rounding**: ROUND_HALF_UP (symmetric rounding)

Symmetric Rounding (ROUND_HALF_UP)
----------------------------------

The quantization algorithm uses symmetric rounding where ties round
**away from zero**:

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Value
     - Quantized (5 decimals)
     - Note
   * - ``0.123456789``
     - ``0.12346``
     - Rounds up (6 > 5)
   * - ``-0.123456789``
     - ``-0.12346``
     - Rounds away from zero
   * - ``0.123455``
     - ``0.12346``
     - Tie rounds up
   * - ``-0.123455``
     - ``-0.12346``
     - Tie rounds away from zero
   * - ``0.0``
     - ``0.0``
     - Zero is fixed point

**Implementation:**

.. code-block:: python

   from babylon.utils.math import quantize

   quantize(0.123456789)   # Returns 0.12346
   quantize(-0.123456789)  # Returns -0.12346
   quantize(0.123455)      # Returns 0.12346 (tie → away from zero)

Precision Configuration
-----------------------

The precision can be adjusted for testing or scenario-specific needs:

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Decimal Places
     - Grid Size
     - Use Case
   * - 1
     - 0.1
     - Coarse (fast tests)
   * - 3
     - 0.001
     - Currency display
   * - **5 (default)**
     - 0.00001
     - Sub-penny precision
   * - 10
     - 0.0000000001
     - Ultra-precise (scientific)

**API:**

.. code-block:: python

   from babylon.utils.math import get_precision, set_precision, quantize

   # Check current precision
   get_precision()  # Returns 5

   # Change precision for testing
   set_precision(3)
   quantize(0.1234)  # Returns 0.123

   # Restore default
   set_precision(5)

Constrained Types Integration
-----------------------------

Pydantic constrained types automatically apply quantization:

.. code-block:: python

   from babylon.models import Probability, Currency, Ratio

   # Quantization happens on assignment
   prob = Probability(0.123456789)
   assert float(prob) == 0.12346

   # This is the Gatekeeper: validation at boundary
   currency = Currency(99.999999)
   assert float(currency) == 100.0

Edge Cases
----------

The quantization function handles edge cases defensively:

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Input
     - Output
     - Behavior
   * - ``None``
     - ``0.0``
     - Treated as zero
   * - ``0.0``
     - ``0.0``
     - Fixed point
   * - Very large
     - Quantized
     - Stable (no overflow)
   * - Very small
     - Quantized
     - Stable (no underflow)

**Idempotency**: Quantizing an already-quantized value returns the same value:

.. code-block:: python

   x = quantize(0.123456789)  # 0.12346
   y = quantize(x)            # 0.12346 (unchanged)
   assert x == y

See Also
--------

- :doc:`/reference/data-models` - Constrained type definitions
- :doc:`/reference/formulas` - Mathematical formulas using quantized values
- :py:mod:`babylon.utils.math` - Source code
