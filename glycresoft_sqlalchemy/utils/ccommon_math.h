#ifndef __PYX_HAVE__glycresoft_sqlalchemy__utils__ccommon_math
#define __PYX_HAVE__glycresoft_sqlalchemy__utils__ccommon_math

struct PeakStruct;
struct MSFeatureStruct;
struct TheoreticalFragmentStruct;
struct FragmentMatchStruct;
struct MatchedSpectrumStruct;
struct IonTypeIndex;
struct IonTypeDoubleMap;
struct PeakStructArray;
struct MSFeatureStructArray;
struct FragmentMatchStructArray;
struct TheoreticalFragmentStructArray;
struct IonSeriesSuite;
struct MatchedSpectrumStructArray;
struct PeakToPeakShiftMatches;

/* "glycresoft_sqlalchemy\utils\ccommon_math.pxd":90
 * # Scalar Structs
 * 
 * cdef public struct PeakStruct:             # <<<<<<<<<<<<<<
 *     float neutral_mass
 *     long id
 */
struct PeakStruct {
  float neutral_mass;
  long id;
  int charge;
  float intensity;
  int rank;
  float mass_charge_ratio;
};

/* "glycresoft_sqlalchemy\utils\ccommon_math.pxd":98
 *     float mass_charge_ratio
 * 
 * cdef public struct MSFeatureStruct:             # <<<<<<<<<<<<<<
 *     float offset
 *     float tolerance
 */
struct MSFeatureStruct {
  float offset;
  float tolerance;
  char *name;
  int intensity_ratio;
  int from_charge;
  int to_charge;
  char *feature_type;
  int min_peak_rank;
  int max_peak_rank;
  struct IonTypeDoubleMap *ion_type_matches;
  struct IonTypeDoubleMap *ion_type_totals;
  int glycan_peptide_ratio;
  int peptide_mass_rank;
};

/* "glycresoft_sqlalchemy\utils\ccommon_math.pxd":113
 *     int peptide_mass_rank
 * 
 * cdef public struct TheoreticalFragmentStruct:             # <<<<<<<<<<<<<<
 *     float neutral_mass
 *     char* key
 */
struct TheoreticalFragmentStruct {
  float neutral_mass;
  char *key;
};

/* "glycresoft_sqlalchemy\utils\ccommon_math.pxd":117
 *     char* key
 * 
 * cdef public struct FragmentMatchStruct:             # <<<<<<<<<<<<<<
 *     double observed_mass
 *     double intensity
 */
struct FragmentMatchStruct {
  double observed_mass;
  double intensity;
  char *key;
  char *ion_type;
  long peak_id;
};

/* "glycresoft_sqlalchemy\utils\ccommon_math.pxd":124
 *     long peak_id
 * 
 * cdef public struct MatchedSpectrumStruct:             # <<<<<<<<<<<<<<
 *     FragmentMatchStructArray* peak_match_list
 *     PeakStructArray* peak_list
 */
struct MatchedSpectrumStruct {
  struct FragmentMatchStructArray *peak_match_list;
  struct PeakStructArray *peak_list;
  char *glycopeptide_sequence;
  int scan_time;
  int peaks_explained;
  int peaks_unexplained;
  int id;
  double peptide_mass;
  double glycan_mass;
  int peptide_mass_rank;
  int glycan_peptide_ratio;
};

/* "glycresoft_sqlalchemy\utils\ccommon_math.pxd":137
 *     int glycan_peptide_ratio
 * 
 * cdef public struct IonTypeIndex:             # <<<<<<<<<<<<<<
 *     char** names
 *     size_t* indices
 */
struct IonTypeIndex {
  char **names;
  size_t *indices;
  size_t size;
};

/* "glycresoft_sqlalchemy\utils\ccommon_math.pxd":142
 *     size_t size
 * 
 * cdef public struct IonTypeDoubleMap:             # <<<<<<<<<<<<<<
 *     IonTypeIndex* index_ref
 *     double* values
 */
struct IonTypeDoubleMap {
  struct IonTypeIndex *index_ref;
  double *values;
};

/* "glycresoft_sqlalchemy\utils\ccommon_math.pxd":149
 * # Array Structs
 * 
 * cdef public struct PeakStructArray:             # <<<<<<<<<<<<<<
 *     PeakStruct* peaks
 *     Py_ssize_t size
 */
struct PeakStructArray {
  struct PeakStruct *peaks;
  Py_ssize_t size;
};

/* "glycresoft_sqlalchemy\utils\ccommon_math.pxd":153
 *     Py_ssize_t size
 * 
 * cdef public struct MSFeatureStructArray:             # <<<<<<<<<<<<<<
 *     MSFeatureStruct* features
 *     Py_ssize_t size
 */
struct MSFeatureStructArray {
  struct MSFeatureStruct *features;
  Py_ssize_t size;
};

/* "glycresoft_sqlalchemy\utils\ccommon_math.pxd":157
 *     Py_ssize_t size
 * 
 * cdef public struct FragmentMatchStructArray:             # <<<<<<<<<<<<<<
 *     FragmentMatchStruct* matches
 *     size_t size
 */
struct FragmentMatchStructArray {
  struct FragmentMatchStruct *matches;
  size_t size;
};

/* "glycresoft_sqlalchemy\utils\ccommon_math.pxd":161
 *     size_t size
 * 
 * cdef public struct TheoreticalFragmentStructArray:             # <<<<<<<<<<<<<<
 *     TheoreticalFragmentStruct* fragments
 *     size_t size
 */
struct TheoreticalFragmentStructArray {
  struct TheoreticalFragmentStruct *fragments;
  size_t size;
  char *ion_series;
};

/* "glycresoft_sqlalchemy\utils\ccommon_math.pxd":166
 *     char* ion_series
 * 
 * cdef public struct IonSeriesSuite:             # <<<<<<<<<<<<<<
 *     char** ion_series_names
 *     TheoreticalFragmentStructArray** theoretical_series
 */
struct IonSeriesSuite {
  char **ion_series_names;
  struct TheoreticalFragmentStructArray **theoretical_series;
  struct FragmentMatchStructArray **matched_series;
  size_t size;
};

/* "glycresoft_sqlalchemy\utils\ccommon_math.pxd":172
 *     size_t size
 * 
 * cdef public struct MatchedSpectrumStructArray:             # <<<<<<<<<<<<<<
 *     MatchedSpectrumStruct* matches
 *     size_t size
 */
struct MatchedSpectrumStructArray {
  struct MatchedSpectrumStruct *matches;
  size_t size;
};

/* "glycresoft_sqlalchemy\utils\ccommon_math.pxd":176
 *     size_t size
 * 
 * cdef public struct PeakToPeakShiftMatches:             # <<<<<<<<<<<<<<
 *     PeakStruct* peaks
 *     size_t size
 */
struct PeakToPeakShiftMatches {
  struct PeakStruct *peaks;
  size_t size;
  double mass_shift;
  struct PeakStruct *reference;
};

#ifndef __PYX_HAVE_API__glycresoft_sqlalchemy__utils__ccommon_math

#ifndef __PYX_EXTERN_C
  #ifdef __cplusplus
    #define __PYX_EXTERN_C extern "C"
  #else
    #define __PYX_EXTERN_C extern
  #endif
#endif

#ifndef DL_IMPORT
  #define DL_IMPORT(_T) _T
#endif

#endif /* !__PYX_HAVE_API__glycresoft_sqlalchemy__utils__ccommon_math */

#if PY_MAJOR_VERSION < 3
PyMODINIT_FUNC initccommon_math(void);
#else
PyMODINIT_FUNC PyInit_ccommon_math(void);
#endif

#endif /* !__PYX_HAVE__glycresoft_sqlalchemy__utils__ccommon_math */
