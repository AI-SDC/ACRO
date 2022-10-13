ACRO R Notebook
================

``` r
# install.packages("rmarkdown")
# install.packages("haven")
# install.packages("dplyr")
# install.packages("reticulate")
```

## Import Libraries

``` r
library(haven)   # read .dta
library(dplyr)   # pivot tables
```

    ##
    ## Attaching package: 'dplyr'

    ## The following objects are masked from 'package:stats':
    ##
    ##     filter, lag

    ## The following objects are masked from 'package:base':
    ##
    ##     intersect, setdiff, setequal, union

``` r
source("acro.R")  # ACRO
```

## Load Data

``` r
data = read_dta("data/test_data.dta")
data = as.data.frame(data)
data = zap_labels(data)  # Stata data files include extra labels

head(data)
```

    ##     charity grant_type index year inc_activity inc_grants inc_donations
    ## 1 4Children          R     1 2011      2880902    9603182         91404
    ## 2 4Children          R     1 2014      6810520   18768904         58002
    ## 3 4Children          R     1 2015      7199403   21638036        132191
    ## 4 4Children          R     1 2013      5573013   15194731        228844
    ## 5 4Children          R     1 2010      2056816    7335103        110256
    ## 6 4Children          R     1 2012      3626830   11156805        520378
    ##   inc_other inc_total total_costs grants_given  balance  assets staff_costs
    ## 1    310947  12886435    12127472           NA   936023 1219083     6883970
    ## 2    401879  26039304    25493796           NA  1500928 1498835    16836008
    ## 3    512654  29482284    32290108           NA -1462896 2358710    18325680
    ## 4    267156  21263744    20989048           NA   972597  964630    14250237
    ## 5    424628   9926803     9769816           NA   572735 1009155     4674153
    ## 6    354855  15658868    15510024           NA   784600  969693    10238620
    ##   status survivor sh_income_inc_activity sh_staff_inc_activity
    ## 1   dead        0              0.2235608             0.4184943
    ## 2   dead        0              0.2615477             0.4045211
    ## 3   dead        0              0.2441942             0.3928587
    ## 4   dead        0              0.2620899             0.3910821
    ## 5   dead        0              0.2071982             0.4400404
    ## 6   dead        0              0.2316151             0.3542303
    ##   sh_assets_inc_activity sh_income_inc_grants sh_staff_inc_grants
    ## 1               2.363171            0.7452164            1.395006
    ## 2               4.543876            0.7207913            1.114807
    ## 3               3.052263            0.7339335            1.180749
    ## 4               5.777358            0.7145840            1.066279
    ## 5               2.038157            0.7389190            1.569290
    ## 6               3.740184            0.7124912            1.089679
    ##   sh_assets_inc_grants sh_income_inc_donations sh_staff_inc_donations
    ## 1             7.877382             0.007093040            0.013277804
    ## 2            12.522328             0.002227479            0.003445116
    ## 3             9.173674             0.004483744            0.007213430
    ## 4            15.751875             0.010762169            0.016058961
    ## 5             7.268559             0.011106899            0.023588445
    ## 6            11.505503             0.033232160            0.050825015
    ##   sh_assets_inc_donations sh_income_inc_other sh_staff_inc_other
    ## 1              0.07497767          0.02412979         0.04516972
    ## 2              0.03869805          0.01543355         0.02387021
    ## 3              0.05604377          0.01738854         0.02797462
    ## 4              0.23723499          0.01256392         0.01874748
    ## 5              0.10925576          0.04277591         0.09084598
    ## 6              0.53664201          0.02266160         0.03465848
    ##   sh_assets_inc_other sh_staff_inc_total sh_assets_inc_total
    ## 1           0.2550663           1.871948           10.570597
    ## 2           0.2681276           1.546644           17.373030
    ## 3           0.2173451           1.608796           12.499326
    ## 4           0.2769518           1.492168           22.043419
    ## 5           0.4207758           2.123765            9.836747
    ## 6           0.3659457           1.529392           16.148273
    ##   sh_income_total_costs sh_staff_total_costs sh_assets_total_costs
    ## 1             0.9411037             1.761697              9.948029
    ## 2             0.9790506             1.514242             17.009075
    ## 3             1.0952376             1.762014             13.689733
    ## 4             0.9870815             1.472891             21.758652
    ## 5             0.9841855             2.090179              9.681185
    ## 6             0.9904946             1.514855             15.994778
    ##   sh_income_grants_given sh_staff_grants_given sh_assets_grants_given
    ## 1                     NA                    NA                     NA
    ## 2                     NA                    NA                     NA
    ## 3                     NA                    NA                     NA
    ## 4                     NA                    NA                     NA
    ## 5                     NA                    NA                     NA
    ## 6                     NA                    NA                     NA
    ##   sh_income_balance sh_staff_balance sh_assets_balance sh_income_assets
    ## 1        0.07263631       0.13597140         0.7678091       0.09460203
    ## 2        0.05764087       0.08914988         1.0013964       0.05756048
    ## 3       -0.04961949      -0.07982765        -0.6202102       0.08000432
    ## 4        0.04573969       0.06825129         1.0082592       0.04536501
    ## 5        0.05769582       0.12253236         0.5675392       0.10165962
    ## 6        0.05010579       0.07663142         0.8091221       0.06192612
    ##   sh_staff_assets sh_income_staff_costs sh_assets_staff_costs wgt
    ## 1      0.17709011             0.5342028              5.646843   1
    ## 2      0.08902556             0.6465614             11.232729   1
    ## 3      0.12871064             0.6215828              7.769365   1
    ## 4      0.06769221             0.6701660             14.772749   1
    ## 5      0.21590115             0.4708619              4.631749   1
    ## 6      0.09470934             0.6538544             10.558620   1

## Pivot Tables

### ACRO Pivot Table

``` r
index = "grant_type"
values = "inc_grants"
aggfunc = list("mean", "std")

table = acro_pivot_table(data, index=index, values=values, aggfunc=aggfunc)
```

``` r
table
```

    ##     mean  inc_grants std   inc_grants
    ## G         11412787.1       22832202.7
    ## N           134431.9         198873.7
    ## R          8098501.8       32044951.0
    ## R/G       16648272.7       15835324.0

## Linear Models

``` r
# extract relevant columns
df = data[, c("inc_activity", "inc_grants", "inc_donations", "total_costs")]
# drop rows with missing values
df = df[complete.cases(df), ]
# formula to fit
formula = "inc_activity ~ inc_grants + inc_donations + total_costs"
```

### Fit Linear Model

``` r
model = lm(formula=formula, data=df)
summary(model)
```

    ##
    ## Call:
    ## lm(formula = formula, data = df)
    ##
    ## Residuals:
    ##       Min        1Q    Median        3Q       Max
    ## -74574494   -633828   -396927   -259424 277064227
    ##
    ## Coefficients:
    ##                 Estimate Std. Error t value Pr(>|t|)
    ## (Intercept)    3.994e+05  5.313e+05   0.752    0.452
    ## inc_grants    -8.856e-01  2.451e-02 -36.128   <2e-16 ***
    ## inc_donations -6.659e-01  1.628e-02 -40.905   <2e-16 ***
    ## total_costs    8.318e-01  1.054e-02  78.937   <2e-16 ***
    ## ---
    ## Signif. codes:  0 '***' 0.001 '**' 0.01 '*' 0.05 '.' 0.1 ' ' 1
    ##
    ## Residual standard error: 13990000 on 807 degrees of freedom
    ## Multiple R-squared:  0.8943, Adjusted R-squared:  0.8939
    ## F-statistic:  2276 on 3 and 807 DF,  p-value: < 2.2e-16

### ACRO Linear Model

``` r
acro_lm(formula=formula, data=df)
```

    ## <class 'statsmodels.iolib.summary.Summary'>
    ## """
    ##                             OLS Regression Results
    ## ==============================================================================
    ## Dep. Variable:           inc_activity   R-squared:                       0.894
    ## Model:                            OLS   Adj. R-squared:                  0.894
    ## Method:                 Least Squares   F-statistic:                     2276.
    ## Date:                Thu, 13 Oct 2022   Prob (F-statistic):               0.00
    ## Time:                        16:30:34   Log-Likelihood:                -14493.
    ## No. Observations:                 811   AIC:                         2.899e+04
    ## Df Residuals:                     807   BIC:                         2.901e+04
    ## Df Model:                           3
    ## Covariance Type:            nonrobust
    ## =================================================================================
    ##                     coef    std err          t      P>|t|      [0.025      0.975]
    ## ---------------------------------------------------------------------------------
    ## Intercept      3.994e+05   5.31e+05      0.752      0.452   -6.43e+05    1.44e+06
    ## inc_grants       -0.8856      0.025    -36.128      0.000      -0.934      -0.837
    ## inc_donations    -0.6659      0.016    -40.905      0.000      -0.698      -0.634
    ## total_costs       0.8318      0.011     78.937      0.000       0.811       0.853
    ## ==============================================================================
    ## Omnibus:                     1348.637   Durbin-Watson:                   1.424
    ## Prob(Omnibus):                  0.000   Jarque-Bera (JB):          1298161.546
    ## Skew:                          10.026   Prob(JB):                         0.00
    ## Kurtosis:                     197.973   Cond. No.                     1.06e+08
    ## ==============================================================================
    ##
    ## Notes:
    ## [1] Standard Errors assume that the covariance matrix of the errors is correctly specified.
    ## [2] The condition number is large, 1.06e+08. This might indicate that there are
    ## strong multicollinearity or other numerical problems.
    ## """

## Logit/Probit Models

``` r
# extract relevant columns
df = data[, c("survivor", "inc_activity", "inc_grants", "inc_donations", "total_costs")]
# drop rows with missing values
df = df[complete.cases(df), ]
# convert survivor to numeric
df = transform(df, survivor = as.numeric(survivor))
# formula to fit
formula = "survivor ~ inc_activity + inc_grants + inc_donations + total_costs"
```

### Fit Logit Model

``` r
model = glm(formula=formula, data=df, family=binomial(link="logit"))
```

    ## Warning: glm.fit: fitted probabilities numerically 0 or 1 occurred

``` r
summary(model)
```

    ##
    ## Call:
    ## glm(formula = formula, family = binomial(link = "logit"), data = df)
    ##
    ## Deviance Residuals:
    ##     Min       1Q   Median       3Q      Max
    ## -3.5701  -1.1953   0.0203   1.0948   1.3215
    ##
    ## Coefficients:
    ##                 Estimate Std. Error z value Pr(>|z|)
    ## (Intercept)    4.364e-02  9.091e-02   0.480  0.63123
    ## inc_activity   5.790e-08  1.129e-07   0.513  0.60807
    ## inc_grants    -7.977e-08  1.045e-07  -0.764  0.44513
    ## inc_donations  3.638e-07  1.312e-07   2.772  0.00557 **
    ## total_costs    5.649e-08  1.002e-07   0.564  0.57273
    ## ---
    ## Signif. codes:  0 '***' 0.001 '**' 0.01 '*' 0.05 '.' 0.1 ' ' 1
    ##
    ## (Dispersion parameter for binomial family taken to be 1)
    ##
    ##     Null deviance: 1019.00  on 810  degrees of freedom
    ## Residual deviance:  800.92  on 806  degrees of freedom
    ## AIC: 810.92
    ##
    ## Number of Fisher Scoring iterations: 10

### ACRO Logit Model

``` r
acro_glm(formula=formula, data=df, family="logit")
```

    ## <class 'statsmodels.iolib.summary.Summary'>
    ## """
    ##                            Logit Regression Results
    ## ==============================================================================
    ## Dep. Variable:               survivor   No. Observations:                  811
    ## Model:                          Logit   Df Residuals:                      806
    ## Method:                           MLE   Df Model:                            4
    ## Date:                Thu, 13 Oct 2022   Pseudo R-squ.:                  0.2140
    ## Time:                        16:30:34   Log-Likelihood:                -400.46
    ## converged:                       True   LL-Null:                       -509.50
    ## Covariance Type:            nonrobust   LLR p-value:                 4.862e-46
    ## =================================================================================
    ##                     coef    std err          z      P>|z|      [0.025      0.975]
    ## ---------------------------------------------------------------------------------
    ## Intercept         0.0436      0.091      0.480      0.631      -0.135       0.222
    ## inc_activity    5.79e-08   1.13e-07      0.513      0.608   -1.63e-07    2.79e-07
    ## inc_grants    -7.977e-08   1.04e-07     -0.764      0.445   -2.85e-07    1.25e-07
    ## inc_donations  3.638e-07   1.31e-07      2.772      0.006    1.07e-07    6.21e-07
    ## total_costs    5.649e-08      1e-07      0.564      0.573    -1.4e-07    2.53e-07
    ## =================================================================================
    ##
    ## Possibly complete quasi-separation: A fraction 0.17 of observations can be
    ## perfectly predicted. This might indicate that there is complete
    ## quasi-separation. In this case some parameters will not be identified.
    ## """

### Fit Probit Model

``` r
model = glm(formula=formula, data=df, family=binomial(link="probit"))
```

    ## Warning: glm.fit: fitted probabilities numerically 0 or 1 occurred

``` r
summary(model)
```

    ##
    ## Call:
    ## glm(formula = formula, family = binomial(link = "probit"), data = df)
    ##
    ## Deviance Residuals:
    ##     Min       1Q   Median       3Q      Max
    ## -3.3475  -1.2076   0.0083   1.1017   1.2938
    ##
    ## Coefficients:
    ##                 Estimate Std. Error z value Pr(>|z|)
    ## (Intercept)    4.454e-02  5.628e-02   0.791   0.4288
    ## inc_activity   4.114e-08  6.351e-08   0.648   0.5171
    ## inc_grants    -4.297e-08  5.884e-08  -0.730   0.4652
    ## inc_donations  1.358e-07  6.392e-08   2.124   0.0337 *
    ## total_costs    3.473e-08  5.657e-08   0.614   0.5393
    ## ---
    ## Signif. codes:  0 '***' 0.001 '**' 0.01 '*' 0.05 '.' 0.1 ' ' 1
    ##
    ## (Dispersion parameter for binomial family taken to be 1)
    ##
    ##     Null deviance: 1019.00  on 810  degrees of freedom
    ## Residual deviance:  806.49  on 806  degrees of freedom
    ## AIC: 816.49
    ##
    ## Number of Fisher Scoring iterations: 12

### ACRO Probit Model

``` r
acro_glm(formula=formula, data=df, family="probit")
```

    ## <class 'statsmodels.iolib.summary.Summary'>
    ## """
    ##                           Probit Regression Results
    ## ==============================================================================
    ## Dep. Variable:               survivor   No. Observations:                  811
    ## Model:                         Probit   Df Residuals:                      806
    ## Method:                           MLE   Df Model:                            4
    ## Date:                Thu, 13 Oct 2022   Pseudo R-squ.:                  0.2086
    ## Time:                        16:30:34   Log-Likelihood:                -403.24
    ## converged:                       True   LL-Null:                       -509.50
    ## Covariance Type:            nonrobust   LLR p-value:                 7.648e-45
    ## =================================================================================
    ##                     coef    std err          z      P>|z|      [0.025      0.975]
    ## ---------------------------------------------------------------------------------
    ## Intercept         0.0445      0.056      0.791      0.429      -0.066       0.155
    ## inc_activity   4.114e-08   6.54e-08      0.629      0.530   -8.71e-08    1.69e-07
    ## inc_grants    -4.297e-08   6.07e-08     -0.708      0.479   -1.62e-07     7.6e-08
    ## inc_donations  1.357e-07   6.27e-08      2.163      0.031    1.28e-08    2.59e-07
    ## total_costs    3.473e-08   5.84e-08      0.595      0.552   -7.96e-08    1.49e-07
    ## =================================================================================
    ##
    ## Possibly complete quasi-separation: A fraction 0.18 of observations can be
    ## perfectly predicted. This might indicate that there is complete
    ## quasi-separation. In this case some parameters will not be identified.
    ## """

## Finalise

``` r
acro_finalise("r_test.xlsx")
```

    ## $output_0
    ## $output_0$command
    ## [1] "pivot_table()"
    ##
    ## $output_0$summary
    ## [1] "pass"
    ##
    ## $output_0$outcome
    ##                  mean        std
    ##            inc_grants inc_grants
    ## grant_type
    ## G                  ok         ok
    ## N                  ok         ok
    ## R                  ok         ok
    ## R/G                ok         ok
    ##
    ## $output_0$output
    ## $output_0$output[[1]]
    ##                     mean           std
    ##               inc_grants    inc_grants
    ## grant_type
    ## G           1.141279e+07  2.283220e+07
    ## N           1.344319e+05  1.988737e+05
    ## R           8.098502e+06  3.204495e+07
    ## R/G         1.664827e+07  1.583532e+07
    ##
    ##
    ##
    ## $output_1
    ## $output_1$command
    ## [1] "olsr()"
    ##
    ## $output_1$summary
    ## [1] "pass; dof=807.0 >= 10"
    ##
    ## $output_1$outcome
    ## Empty DataFrame
    ## Columns: []
    ## Index: []
    ##
    ## $output_1$output
    ## $output_1$output[[1]]
    ##                        inc_activity           R-squared:      0.894
    ## Dep. Variable:
    ## Model:                          OLS      Adj. R-squared:      0.894
    ## Method:               Least Squares         F-statistic:   2276.000
    ## Date:              Thu, 13 Oct 2022  Prob (F-statistic):      0.000
    ## Time:                      16:30:33      Log-Likelihood: -14493.000
    ## No. Observations:               811                 AIC:  28990.000
    ## Df Residuals:                   807                 BIC:  29010.000
    ## Df Model:                         3                  NaN        NaN
    ## Covariance Type:          nonrobust                  NaN        NaN
    ##
    ## $output_1$output[[2]]
    ##                       coef     std err       t  P>|t|      [0.025       0.975]
    ## Intercept      399400.0000  531000.000   0.752  0.452 -643000.000  1440000.000
    ## inc_grants         -0.8856       0.025 -36.128  0.000      -0.934       -0.837
    ## inc_donations      -0.6659       0.016 -40.905  0.000      -0.698       -0.634
    ## total_costs         0.8318       0.011  78.937  0.000       0.811        0.853
    ##
    ## $output_1$output[[3]]
    ##                 1348.637     Durbin-Watson:         1.424
    ## Omnibus:
    ## Prob(Omnibus):     0.000  Jarque-Bera (JB):  1.298162e+06
    ## Skew:             10.026          Prob(JB):  0.000000e+00
    ## Kurtosis:        197.973          Cond. No.  1.060000e+08
    ##
    ##
    ##
    ## $output_2
    ## $output_2$command
    ## [1] "logitr()"
    ##
    ## $output_2$summary
    ## [1] "pass; dof=806.0 >= 10"
    ##
    ## $output_2$outcome
    ## Empty DataFrame
    ## Columns: []
    ## Index: []
    ##
    ## $output_2$output
    ## $output_2$output[[1]]
    ##                           survivor No. Observations:           811
    ## Dep. Variable:
    ## Model:                       Logit     Df Residuals:  8.060000e+02
    ## Method:                        MLE         Df Model:  4.000000e+00
    ## Date:             Thu, 13 Oct 2022    Pseudo R-squ.:  2.140000e-01
    ## Time:                     16:30:34   Log-Likelihood: -4.004600e+02
    ## converged:                    True          LL-Null: -5.095000e+02
    ## Covariance Type:         nonrobust      LLR p-value:  4.862000e-46
    ##
    ## $output_2$output[[2]]
    ##                        coef       std err  ...        [0.025        0.975]
    ## Intercept      4.360000e-02  9.100000e-02  ... -1.350000e-01  2.220000e-01
    ## inc_activity   5.790000e-08  1.130000e-07  ... -1.630000e-07  2.790000e-07
    ## inc_grants    -7.977000e-08  1.040000e-07  ... -2.850000e-07  1.250000e-07
    ## inc_donations  3.638000e-07  1.310000e-07  ...  1.070000e-07  6.210000e-07
    ## total_costs    5.649000e-08  1.000000e-07  ... -1.400000e-07  2.530000e-07
    ##
    ## [5 rows x 6 columns]
    ##
    ##
    ##
    ## $output_3
    ## $output_3$command
    ## [1] "probitr()"
    ##
    ## $output_3$summary
    ## [1] "pass; dof=806.0 >= 10"
    ##
    ## $output_3$outcome
    ## Empty DataFrame
    ## Columns: []
    ## Index: []
    ##
    ## $output_3$output
    ## $output_3$output[[1]]
    ##                           survivor No. Observations:           811
    ## Dep. Variable:
    ## Model:                      Probit     Df Residuals:  8.060000e+02
    ## Method:                        MLE         Df Model:  4.000000e+00
    ## Date:             Thu, 13 Oct 2022    Pseudo R-squ.:  2.086000e-01
    ## Time:                     16:30:34   Log-Likelihood: -4.032400e+02
    ## converged:                    True          LL-Null: -5.095000e+02
    ## Covariance Type:         nonrobust      LLR p-value:  7.648000e-45
    ##
    ## $output_3$output[[2]]
    ##                        coef       std err  ...        [0.025        0.975]
    ## Intercept      4.450000e-02  5.600000e-02  ... -6.600000e-02  1.550000e-01
    ## inc_activity   4.114000e-08  6.540000e-08  ... -8.710000e-08  1.690000e-07
    ## inc_grants    -4.297000e-08  6.070000e-08  ... -1.620000e-07  7.600000e-08
    ## inc_donations  1.357000e-07  6.270000e-08  ...  1.280000e-08  2.590000e-07
    ## total_costs    3.473000e-08  5.840000e-08  ... -7.960000e-08  1.490000e-07
    ##
    ## [5 rows x 6 columns]
