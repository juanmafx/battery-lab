# Statistical methods

This page covers how `battery-lab trend` estimates capacity loss, what it costs, and where it can
mislead you.

## Pipeline

1. **Daily medians.** Health readings are reduced to one median per UTC day. A 5-minute cron log
   holds hundreds of nearly identical readings per day, and treating them as independent would
   inflate significance.
2. **Theil-Sen slope.** The slope is the median of all pairwise slopes between days. It tolerates
   outliers up to a breakdown point of about 29%, which suits firmware that occasionally
   recalibrates.
3. **Mann-Kendall test.** A rank-based test for a monotonic trend, with the tie correction to its
   variance. Tie handling matters because firmware reports capacity in discrete steps.
4. **Hamed-Rao correction.** Variance is inflated using significant lags of the rank
   autocorrelation of the detrended series. The factor is floored at 1, so it never makes the test
   less conservative.
5. **Confidence interval.** The rank-based interval for the Sen slope, using the corrected
   variance, with linear interpolation between order statistics.
6. **Projection.** Only for a statistically significant decline, the fitted line is extended to
   the threshold. The range comes from the slope interval alone.

## Complexity

For `n` measured days and `P = min(n(n-1)/2, 250000)` slope pairs:

| Step | Time | Space |
|---|---|---|
| Daily medians, `m` samples | `O(m log m)` | `O(m)` |
| Kendall S with a Fenwick tree | `O(n log n)` | `O(n)` |
| Tie-corrected variance | `O(n)` expected | `O(n)` |
| Hamed-Rao, `L = ceil(10 log10 n)` lags | `O(n L)` | `O(n)` |
| Theil-Sen slopes and interval | `O(P log P)` | `O(P)` |

All pairs are used up to 250,000 pairs, which is 707 measured days. Beyond that, pairs are sampled
uniformly with a seeded generator, and the output says so.

## Reproducibility

- `trend --seed` fixes pair sampling. Below the pair limit the result does not depend on the seed.
- `simulate --seed` produces an identical log for the same arguments.
- The test suite runs with `--hypothesis-seed=2026` and fixed Monte Carlo seeds.
- `scripts/validate_estimators.py` regenerates
  [reports/validation/estimators.txt](../reports/validation/estimators.txt).

## Measured estimator behavior

From the committed validation run: 2,000 simulated series of length 60 per scenario, seed 2026,
nominal false positive rate 5%.

| Scenario | Result |
|---|---|
| White noise, false positive rate | 4.0% |
| 95% interval coverage, linear signal with white noise | 95.6% |
| AR(1) rho 0.3, false positives, uncorrected / corrected | 14.3% / 10.7% |
| AR(1) rho 0.6, false positives, uncorrected / corrected | 30.2% / 16.7% |
| AR(1) rho 0.9, false positives, uncorrected / corrected | 62.8% / 32.8% |

These are simulations, not measurements of real batteries.

## Limitations

- **The correction reduces autocorrelation bias but does not remove it.** With strong
  autocorrelation the false positive rate stays well above nominal, as the table shows. Firmware
  capacity values move in steps, so treat a "declining" verdict on a short log with caution.
- Battery fade is not linear over a whole lifetime. Long projections are rough.
- The projection range reflects slope uncertainty only, not model error, heat or usage changes.
- Missing days are treated as a shorter sequence by the autocorrelation step.
- Readings are the firmware's own estimate of full capacity, which can jump after a calibration.

## References

- Mann, H. B. (1945). Nonparametric tests against trend. *Econometrica*, 13(3).
- Kendall, M. G. (1975). *Rank Correlation Methods*. Griffin.
- Theil, H. (1950). A rank-invariant method of linear and polynomial regression analysis.
- Sen, P. K. (1968). Estimates of the regression coefficient based on Kendall's tau. *JASA*, 63(324).
- Hamed, K. H. and Rao, A. R. (1998). A modified Mann-Kendall trend test for autocorrelated data.
  *Journal of Hydrology*, 204.
- Gilbert, R. O. (1987). *Statistical Methods for Environmental Pollution Monitoring*. Van Nostrand Reinhold.

---

Next: [Known quirks](quirks.md)

[Documentation index](README.md) · [Project README](../README.md)
