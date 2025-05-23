## Binary file format

### Header

Byte 1: integer denoting the version number. This helps a new version of the script read an older version of the binary file, a situation that might arise due to caching problems.

Byte 2: integer denoting the length of the video id, denoted by $|id|$.

Byte 3-4: reserved.

Byte 5-8: big-endian integer $n$ which denotes the number of data entries in this file.

### Content

The remainder of the file contains $n$ entries taking up $(|id| + 2) \cdot n$ bytes.

For each entry, the first $|id|$ bytes record the video id. 

In the remaining 2 bytes, the first 10 bits record the 3 most significant digits of the view count. The last 6 bits record the number of 0s that need to be appended to the previous 10 bits to get the view count. 

For example, 12345 would first be floored to get 12300. The first 10 bits would store 123, while the last 6 bits would store 2 (since there are 2 zeros after flooring). 

