#define _USE_MATH_DEFINES
#include <cmath>
#include <algorithm>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#ifdef _OPENMP
#include <omp.h>
#endif

extern "C" {
    __declspec(dllexport) void compute_geomorphons(
        const double* heights,
        int nrows,
        int ncols,
        double* geo_results,
        int L,
        double threshold
    ) {
        // Matriz de lookup para geomorphons
        const int GEOMORPHONS_MATRIX[9][9] = {
            {4, 4, 4, 3, 3, 1, 1, 1, 0},
            {4, 4, 3, 3, 3, 1, 1, 1, -1},
            {4, 6, 5, 5, 2, 2, 1, -1, -1},
            {6, 6, 5, 5, 5, 2, -1, -1, -1},
            {6, 6, 7, 5, 5, -1, -1, -1, -1},
            {8, 8, 7, 7, -1, -1, -1, -1, -1},
            {8, 8, 8, -1, -1, -1, -1, -1, -1},
            {8, 8, -1, -1, -1, -1, -1, -1, -1},
            {9, -1, -1, -1, -1, -1, -1, -1, -1}
        };
        
        L += 1;
        
        // Direções: E, SE, S, SW, W, NW, N, NE
        const int col_values[8] = {1, 1, 0, -1, -1, -1, 0, 1};
        const int row_values[8] = {0, 1, 1, 1, 0, -1, -1, -1};
        double distance_values[8];
        const double convert_angle = 180.0 / M_PI;
        
        for (int i = 0; i < 8; i++) {
            distance_values[i] = std::sqrt(col_values[i] * col_values[i] + 
                                          row_values[i] * row_values[i]);
        }
        
        // Processa cada pixel
        #pragma omp parallel for schedule(static)
        for (int num_line = 1; num_line < nrows - 1; num_line++) {
            for (int num_cols = 1; num_cols < ncols - 1; num_cols++) {
                int positive = 0;
                int negative = 0;
                
                double center_height = heights[num_line * ncols + num_cols];
                
                // Analisa cada direção
                for (int direction = 0; direction < 8; direction++) {
                    int row_increment = row_values[direction];
                    int col_increment = col_values[direction];
                    double dist_inc = distance_values[direction];
                    int steps = static_cast<int>(L / dist_inc);
                    
                    int valid_count = 0;
                    double max_angle = -1e300;
                    double min_angle = 1e300;
                    
                    // Percorre ao longo da direção
                    for (int step = 1; step < steps; step++) {
                        int r = num_line + step * row_increment;
                        int c = num_cols + step * col_increment;
                        
                        if ((unsigned)r >= (unsigned)nrows || (unsigned)c >= (unsigned)ncols) {
                            break;
                        }
                        
                        double d = step * dist_inc;
                        double dh = heights[r * ncols + c] - center_height;
                        double angle = std::atan(dh / d) * (convert_angle);
                        
                        if (!std::isnan(angle)) {
                            if (angle > max_angle) max_angle = angle;
                            if (angle < min_angle) min_angle = angle;
                            valid_count++;
                        }
                    }
                    
                    if (valid_count == 0) continue;
                    
                    // Classifica a direção
                    const double diff = max_angle - std::abs(min_angle);

                    if (diff > threshold) {
                        positive++;
                    } else if (std::abs(diff) <= threshold) {
                        // neutral - não faz nada
                    } else {
                        negative++;
                    }
                }
                
                // Atribui o resultado
                geo_results[num_line * ncols + num_cols] = 
                    GEOMORPHONS_MATRIX[negative][positive];
            }
        }
    }
}