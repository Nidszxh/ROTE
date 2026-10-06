# ROTE evaluation

## Strategy summary

| Strategy | θ | Metric | Mean | 95% CI | n |
| --- | ---: | --- | ---: | --- | ---: |
| depth_proportional | 0.25 | shortfall_bps | 10.8933 | [7.3440, 14.9831] | 200 |
| depth_proportional | 0.25 | risk | 2.7896 | [2.3864, 3.2733] | 200 |
| depth_proportional | 0.5 | shortfall_bps | 11.9857 | [8.4665, 15.9137] | 200 |
| depth_proportional | 0.5 | risk | 3.0702 | [2.6196, 3.6463] | 200 |
| depth_proportional | 1 | shortfall_bps | 15.2264 | [12.0396, 18.8952] | 200 |
| depth_proportional | 1 | risk | 3.7869 | [3.2703, 4.3647] | 200 |
| depth_proportional | 2 | shortfall_bps | 19.6003 | [16.2159, 23.4167] | 200 |
| depth_proportional | 2 | risk | 4.1301 | [3.4712, 4.8201] | 200 |
| depth_proportional | 5 | shortfall_bps | 30.3520 | [26.0883, 35.0858] | 200 |
| depth_proportional | 5 | risk | 5.7893 | [4.8074, 6.7473] | 200 |
| twap_T | 0.25 | shortfall_bps | 10.8182 | [7.3077, 14.7479] | 200 |
| twap_T | 0.25 | risk | 2.7909 | [2.3727, 3.2583] | 200 |
| twap_T | 0.5 | shortfall_bps | 11.9346 | [8.5212, 16.0465] | 200 |
| twap_T | 0.5 | risk | 3.0167 | [2.5332, 3.6053] | 200 |
| twap_T | 1 | shortfall_bps | 15.1344 | [11.9147, 18.8616] | 200 |
| twap_T | 1 | risk | 3.7630 | [3.1404, 4.4879] | 200 |
| twap_T | 2 | shortfall_bps | 19.5625 | [16.3802, 23.4665] | 200 |
| twap_T | 2 | risk | 4.2254 | [3.5145, 4.9776] | 200 |
| twap_T | 5 | shortfall_bps | 30.2285 | [25.9822, 35.0107] | 200 |
| twap_T | 5 | risk | 5.8814 | [4.8066, 6.8589] | 200 |

## Holm-corrected paired comparisons

| Comparison | Difference | p | Holm p | Reject |
| --- | ---: | ---: | ---: | --- |
| depth_proportional - twap_T | 0.0759 | 0.0015 | 0.0015 | True |
